import threading
import time
import random

class SemaphoreManual:
    def __init__(self, value=1):
        self.value = value
        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)

    def acquire(self):
        with self.condition:
            while self.value == 0:
                self.condition.wait()
            self.value -= 1

    def release(self):
        with self.condition:
            self.value += 1
            self.condition.notify()


N = 5

compilador = SemaphoreManual(1)
banco = SemaphoreManual(2)

print_lock = threading.Lock()
evento_id = 0

def log(msg):
    global evento_id
    with print_lock:
        evento_id += 1
        print(f"{evento_id:04d} | {msg}")

def pensar(id):
    print(f"[P{id}] pensando...")
    time.sleep(random.uniform(1, 3))


def compilar(id):
    print(f"[P{id}] COMPILANDO...")
    time.sleep(random.uniform(1, 2))


def programador(id):
    while True:
        pensar(id)

        print(f"[P{id}] quer acessar o banco")
        banco.acquire()
        print(f"[P{id}] entrou no banco")

        print(f"[P{id}] quer usar o compilador")
        compilador.acquire()
        print(f"[P{id}] pegou o compilador")

        compilar(id)

        print(f"[P{id}] terminou compilação")

        compilador.release()
        print(f"[P{id}] liberou compilador")

        banco.release()
        print(f"[P{id}] saiu do banco")


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