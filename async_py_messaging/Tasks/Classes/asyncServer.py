import asyncServerClass
import load_config

def main():
    """Server main function"""
    config = load_config.load_config({})
    server = asyncServerClass.ServerTask(config)
    server.start()
    server.join()


if __name__ == "__main__":
    main()


