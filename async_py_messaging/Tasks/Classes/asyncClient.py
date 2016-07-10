import asyncClientClass
import os
import load_config

def main():
    """Client main function"""
    config = {'id': os.getpid()}
    config = load_config.load_config(config)
    for i in range(3):
        client = asyncClientClass.ClientTask(os.getpid(), config)
        client.start()



if __name__ == "__main__":
    main()


