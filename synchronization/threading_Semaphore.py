import threading
import time
import random

N = 5

compilador = threading.Semaphore(1)
banco = threading.Semaphore(2)

print_lock = threading.Lock()
evento_id = 0

def log(msg):
    global evento_id
    with print_lock:
        evento_id += 1
        print(f"{evento_id:04d} | {msg}")

def pensar(id):
    log(f"[P{id}] pensando...")
    time.sleep(random.uniform(1, 3))

def compilar(id):
    log(f"[P{id}] COMPILANDO...")
    time.sleep(random.uniform(1, 2))

def programador(id):
    while True:
        pensar(id)

        log(f"[P{id}] quer acessar o banco")
        banco.acquire()
        log(f"[P{id}] entrou no banco")

        log(f"[P{id}] quer usar o compilador")
        compilador.acquire()
        log(f"[P{id}] pegou o compilador")

        compilar(id)

        log(f"[P{id}] terminou compilação")

        compilador.release()
        log(f"[P{id}] liberou compilador")

        banco.release()
        log(f"[P{id}] saiu do banco")

def main():
    threads = []

    for i in range(N):
        t = threading.Thread(target=programador, args=(i+1,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

if __name__ == "__main__":
    main()