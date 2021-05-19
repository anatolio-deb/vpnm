import time
from threading import Thread


def animate(thread: Thread) -> None:
    animation = "|/-\\"
    idx = 0
    while thread.is_alive():
        print(animation[idx % len(animation)], end="\r")
        idx += 1
        time.sleep(0.1)
