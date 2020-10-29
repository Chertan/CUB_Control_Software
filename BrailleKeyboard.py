import time


def main(out_pipe=None, in_pipe=None):
    # Perform Simulated input

    test_input = ['<uppercase>', 't', 'h', 'i', 's', ' ', 'i', 's', ' ', 'a', ' ', 't', 'e', 's', 't', '.']
    i = 0

    while not in_pipe.poll():
        out_pipe.send(test_input[i])
        i += 1
        time.sleep(0.5)


if __name__ == "__main__":
    main()
