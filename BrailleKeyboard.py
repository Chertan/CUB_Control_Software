import time


def main(pipe=None):
    # Perform Simulated input

    test_input = ['<uppercase>', 't', 'h', 'i', 's', ' ', 'i', 's', ' ', 'a', ' ', 't', 'e', 's', 't', '.', "END OF INPUT"]
    i = 0

    while not pipe.poll():
        pipe.send(test_input[i])
        i += 1
        time.sleep(0.5)


if __name__ == "__main__":
    main()
