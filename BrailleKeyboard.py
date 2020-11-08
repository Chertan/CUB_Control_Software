import time

# Note the main function of the braille keyboard should import a pipe item to send input to
# can use if statement below to still allow operation without the pipe
# Statement send input to the CUB if the pipe is defined, otherwise no addition is present


def main(pipe=None):
    # Perform Simulated input

    test_input = ['<uppercase>', 't', 'h', 'i', 's', ' ', 'i', 's', ' ', 'a', ' ', 't', 'e', 's', 't', '.',
                  "END OF INPUT"]
    i = 0

    while not pipe.poll():

        if pipe is not None:
            pipe.send(test_input[i])
            i += 1
            time.sleep(0.5)


if __name__ == "__main__":
    main()
