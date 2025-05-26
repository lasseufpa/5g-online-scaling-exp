import subprocess
from concurrent.futures import ProcessPoolExecutor
import os
from collections import defaultdict

## Edit herer ###############
INPUT_DIR = "input"
SIMULADOR = "simulador.py"
MAX_WORKERS = 5
############################

def run_simulator_with_flag(args):
    dataset_path, ideal = args
    run_simulator(dataset_path, ideal)

def run_simulator(dataset_path, ideal=False):
    try:
        command = ["python3", SIMULADOR, dataset_path]
        if ideal:
            command += ["--ideal", "true"]
        
        subprocess.run(command, check=True)
        modo = "Ideal" if ideal else "Padrão"
        print(f"Execution completed for {os.path.basename(dataset_path)} ({modo})")
    except subprocess.CalledProcessError as e:
        print(f"Error executing {dataset_path}: {e}")

def get_csv_files(input_dir):
    """Retorna a lista de caminhos dos arquivos .csv na pasta input."""
    return [os.path.join(input_dir, f) for f in os.listdir(input_dir) if f.endswith(".csv")]        

def cluster_models(csv_files):
    """Agrupa os arquivos por modelo (prefixo antes do '_')."""
    cluster = defaultdict(list)
    for f in csv_files:
        name = os.path.basename(f)
        modelo = name.split('_')[0]
        cluster[modelo].append(f)
    return cluster


def main():
    csv_files = get_csv_files(INPUT_DIR)

    model_groups = cluster_models(csv_files)
    print(" Models found:")
    for modelo, arquivos in model_groups.items():
        nomes = [os.path.basename(a) for a in sorted(arquivos)]
        print(f"  - {modelo}: {', '.join(nomes)}")

    print("\n Running base models...")
    for f in csv_files:
        print(f"{os.path.basename(f)}")
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        executor.map(run_simulator_with_flag, [(f, False) for f in csv_files])

    # Seleciona o primeiro modelo para rodar no modo ideal
    first_model = next(iter(model_groups))
    arquivos_ideais = sorted(model_groups[first_model], key=lambda x: int(os.path.basename(x).split('_')[1].split('.')[0]))

    print(f"\n Running ideal model ({first_model})...")
    for f in arquivos_ideais:
        print(f"{os.path.basename(f)} (Ideal)")
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        executor.map(run_simulator_with_flag, [(f, True) for f in arquivos_ideais])
if __name__ == "__main__":
    main()

