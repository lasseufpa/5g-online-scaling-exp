import simpy
import pandas as pd
import os
import time
import argparse

metrics = {
    "time": [],
    "unallocated_requests": [],
    "total_requests": [],
    "lost_percentage": [],
    "amf_utilization": []
}
active_amfs_over_time = []
Active_ON = []

class AMF:
    def __init__(self, env, id, capacity, creation_time, life):
        self.env = env
        self.id = id
        self.capacity = capacity
        self.creation_time = creation_time
        self.life = life
        self.requisitions = []
        self.state = "OFF"
        self.shutdown_state = None
        self.reduced_capacity = capacity
        self.shutdown_end_time = None

    def turnOn(self):
        if self.state == "OFF":
            yield self.env.timeout(self.creation_time)
            self.state = "ON"

    def turnOff(self):
        if self.state in ["ON", "SHUTTING_DOWN"]:
            self.state = "OFF"
            self.shutdown_state = None
            self.reduced_capacity = self.capacity

    def requition_process(self, req):
        if self.state in ["ON", "SHUTTING_DOWN"] and len(self.requisitions) < self.reduced_capacity:
            self.requisitions.append(req)
            self.env.process(req.exec(self))
            return True
        return False

    def finalize_request(self, req):
        if req in self.requisitions:
            self.requisitions.remove(req)

class Requisition:
    def __init__(self, env, time_exec):
        self.env = env
        self.time_exec = time_exec - 1

    def exec(self, AMF):
        yield self.env.timeout(self.time_exec)
        AMF.finalize_request(self)

class InstanceManager:
    def __init__(self, env, AMF_capacity, creation_time, life, damage):
        self.env = env
        self.AMF_capacity = AMF_capacity
        self.creation_time = creation_time
        self.life = life
        self.damage = damage
        self.AMFs = []
        self.AMF_count = 0
        self.last_assigned_amf = -1

    def create_initial_amfs(self, num_amfs):
        for i in range(num_amfs):
            initial_life = float('inf') if i == 0 else self.life
            instance = AMF(self.env, id=self.AMF_count, capacity=self.AMF_capacity, creation_time=self.creation_time, life=initial_life)
            self.AMF_count += 1
            instance.state = "ON"
            self.AMFs.append(instance)

    def allocate_requisitions(self, num_requisitions, fixed_time_exec):
        unallocated = 0
        num_amfs = len(self.AMFs)

        if num_amfs == 0:
            return num_requisitions

        for _ in range(num_requisitions):
            allocated = False
            start_index = (self.last_assigned_amf + 1) % num_amfs

            for i in range(num_amfs):
                current_index = (start_index + i) % num_amfs
                amf = self.AMFs[current_index]

                if amf.state in ["ON", "SHUTTING_DOWN"] and len(amf.requisitions) < amf.reduced_capacity:
                    req = Requisition(self.env, fixed_time_exec)
                    amf.requition_process(req)
                    self.last_assigned_amf = current_index
                    allocated = True
                    break

            if not allocated:
                unallocated += 1

        return unallocated

    def manage_shutdown(self, amf, time_exec):
        if amf.state == "ON" and amf.life <= 0:
            amf.state = "SHUTTING_DOWN"
            amf.shutdown_state = 1
            amf.reduced_capacity = amf.capacity * 0.05
            amf.shutdown_end_time = self.env.now + time_exec
        elif amf.state == "SHUTTING_DOWN" and amf.shutdown_state == 1 and self.env.now >= amf.shutdown_end_time:
            amf.shutdown_state = 2
            amf.reduced_capacity = amf.capacity * 0.01
            amf.shutdown_end_time = self.env.now + time_exec
        elif amf.state == "SHUTTING_DOWN" and amf.shutdown_state == 2 and self.env.now >= amf.shutdown_end_time:
            amf.turnOff()

    def decrement_life(self):
        for amf in self.AMFs:
            if amf.state == "ON":
                amf.life -= self.damage
                self.manage_shutdown(amf, 10)
            elif amf.state == "SHUTTING_DOWN":
                self.manage_shutdown(amf, 10)

    def adjust_amfs_life(self, required_amfs):
        current_on_amfs = [amf for amf in self.AMFs if amf.state == "ON"]
        num_on_amfs = len(current_on_amfs)

        if required_amfs > num_on_amfs:
            for amf in current_on_amfs:
                amf.life += self.damage
            for _ in range(required_amfs - num_on_amfs):
                self.create_AMF()
        elif required_amfs == num_on_amfs:
            for amf in current_on_amfs:
                amf.life += self.damage
        elif required_amfs < num_on_amfs:
            for i, amf in enumerate(current_on_amfs):
                if i < required_amfs:
                    amf.life += self.damage
                else:
                    amf.life = max(amf.life, 0)

    def create_AMF(self):
        instance = AMF(self.env, id=self.AMF_count, capacity=self.AMF_capacity, creation_time=self.creation_time, life=self.life)
        self.AMF_count += 1
        instance.state = "ON"
        self.AMFs.append(instance)

    def manage_life_and_instances(self, required_amfs):
        self.decrement_life()
        self.adjust_amfs_life(required_amfs)
        if all(amf.state != "ON" for amf in self.AMFs):
            self.create_AMF()

def calculate_required_amfs(total_requisitions, amf_capacity, utilization_percentage):
    required_amfs = (total_requisitions / amf_capacity) * (100 / utilization_percentage)
    return int(required_amfs) + (1 if required_amfs % 1 > 0 else 0)

def log_amf_states(env, manager, log_file, total_requests, used_for_prediction, unallocated):
    active_amfs = len([amf for amf in manager.AMFs if amf.state in ["ON", "SHUTTING_DOWN"]])
    active_amfs_over_time.append(active_amfs)
    active_on = len([amf for amf in manager.AMFs if amf.state == "ON"])
    Active_ON.append(active_on)

    with open(log_file, "a") as file:
        file.write(f"Time {env.now}, Total Requests: {total_requests}, Predicted: {used_for_prediction}, Unallocated: {unallocated} #######################\n")
        for amf in manager.AMFs:
            state = amf.state
            if amf.shutdown_state == 1:
                max_capacity = amf.capacity * 0.05
            elif amf.shutdown_state == 2:
                max_capacity = amf.capacity * 0.01
            else:
                max_capacity = amf.capacity
            shutdown_info = f"Shutdown State: {amf.shutdown_state}" if amf.shutdown_state else " "
            file.write(f"AMF ID: {amf.id}, State: {state}, Life: {amf.life}, Reqs: {len(amf.requisitions)} (Max Capacity: {max_capacity:.0f}), {shutdown_info}\n")
        file.write("\n")

def requisition_event(env, manager, real_requests, required_amfs, time_exec, event_time, used_for_prediction, log_file):
    global metrics
    yield env.timeout(event_time - env.now)

    manager.manage_life_and_instances(required_amfs)
    unallocated = manager.allocate_requisitions(real_requests, time_exec)

    metrics["time"].append(event_time)
    metrics["unallocated_requests"].append(unallocated)
    metrics["total_requests"].append(real_requests)
    lost_percentage = (unallocated / real_requests) * 100 if real_requests > 0 else 0
    metrics["lost_percentage"].append(lost_percentage)

    total_capacity = sum(
        amf.reduced_capacity if amf.state == "SHUTTING_DOWN" else amf.capacity
        for amf in manager.AMFs if amf.state in ["ON", "SHUTTING_DOWN"]
    )
    total_requisitions = sum(
        len(amf.requisitions)
        for amf in manager.AMFs if amf.state in ["ON", "SHUTTING_DOWN"]
    )
    utilization_percentage = (total_requisitions / total_capacity) * 100 if total_capacity > 0 else 0
    metrics["amf_utilization"].append(utilization_percentage)

    log_amf_states(env, manager, log_file, real_requests, used_for_prediction, unallocated)

def save_to_csv(data, filename):
    os.makedirs("output", exist_ok=True)
    file_path = os.path.join("output", filename)
    data.to_csv(file_path, index=False)

def main(dataset_name, ideal=False):
    requests_per_second = 20
    utilization_percentage = 80
    amf_capacity = requests_per_second * 600
    time_exec = 10
    creation_time = 0
    life = 2
    damage = 1

    data = pd.read_csv(dataset_name)
    first_row = data.iloc[0]
    initial_reqs = first_row['Real_Requests'] if ideal else first_row['Predicted_Requests']
    initial_required_amfs = calculate_required_amfs(initial_reqs, amf_capacity, utilization_percentage)

    basename = os.path.basename(dataset_name).split('.')[0]  # Ex: "BLR_1"
    prefix = f"Ideal_{basename.split('_')[-1]}" if ideal else basename
    log_file = os.path.join("output", f"{prefix}_states_log.txt")
    os.makedirs("output", exist_ok=True)
    with open(log_file, "w") as file:
        file.write("Log of AMF states over time\n")

    env = simpy.Environment()
    manager = InstanceManager(env, AMF_capacity=amf_capacity, creation_time=creation_time, life=life, damage=damage)
    manager.create_initial_amfs(initial_required_amfs)

    for idx, row in data.iterrows():
        event_time = idx * time_exec
        used_prediction = row['Real_Requests'] if ideal else row['Predicted_Requests']
        required_amfs = calculate_required_amfs(used_prediction, amf_capacity, utilization_percentage)

        env.process(requisition_event(env, manager, row['Real_Requests'], required_amfs, time_exec, event_time, used_prediction, log_file))

    simulation_time = len(data) * time_exec
    env.run(until=simulation_time)

    save_to_csv(pd.DataFrame({
        "Time": metrics["time"],
        "Unallocated Requests": metrics["unallocated_requests"]
    }), f"{prefix}_unallocated_requests.csv")

    save_to_csv(pd.DataFrame({
        "Time": metrics["time"],
        "AMF Utilization (%)": metrics["amf_utilization"]
    }), f"{prefix}_amf_utilization.csv")

    save_to_csv(pd.DataFrame({
        "Time": [i * time_exec for i in range(len(active_amfs_over_time))],
        "Active AMFs": active_amfs_over_time
    }), f"{prefix}_active_amfs_log.csv")

    save_to_csv(pd.DataFrame({
        "Time": [i * time_exec for i in range(len(Active_ON))],
        "ON AMFs": Active_ON
    }), f"{prefix}_ON_amfs_log.csv")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulador de AMF")
    parser.add_argument("dataset", type=str, help="Nome do arquivo de dataset (ex: data.csv)")
    parser.add_argument("--ideal", type=str, default="false", help="Usar modo ideal (true/false)")
    args = parser.parse_args()

    ideal_mode = args.ideal.lower() == "true"
    main(args.dataset, ideal=ideal_mode)
