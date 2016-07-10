import asyncServerClass
import asyncClientClass

def main():
    """main function"""
    server = asyncServerClass.ServerTask()
    server.start()
    for i in range(3):
        client = asyncClientClass.ClientTask(i)
        client.start()

    server.join()


if __name__ == "__main__":
    main()

