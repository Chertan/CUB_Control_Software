from component_control.ToolSelector import ToolSelector
import logging
import time


def main():
    logging.basicConfig(level=logging.INFO)

    tool = ""

    try:
        tool = ToolSelector()

        if isinstance(tool, ToolSelector):
            print("ToolSelector Successfully Initialised")

        while True:

            for i in range(0, 10):
                tool.tool_select((i*20) % 8)
                time.sleep(0.5)

    except KeyboardInterrupt:
        if isinstance(tool, ToolSelector):
            tool.emergency_stop()


if __name__ == '__main__':
    main()
