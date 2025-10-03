from xnat_listener import XNATlistener
from RabbitMQ_messenger import messenger
from config_handler import Config
import time
import logging
import os


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger()

class Runner:
    def __init__(self):
        if os.path.exists("/app/data/processed_ids.txt"):
            with open("/app/data/processed_ids.txt") as f:
                logging.info("Processed_ids.txt file has been found")
                self.processed_ids = [line.strip() for line in f if line.strip()]
        else:
            logging.info("No processed_ids.txt file has been found")
            self.processed_ids = []
                
        self.next_queue = Config("xnat_listener")["send_queue"]
    
    def Initiate_listener(self):
        listener = XNATlistener()
        downloaded_ids = listener.run(self.processed_ids)

        new_ids = []

        for id in downloaded_ids:
            if id not in self.processed_ids:
                logging.info(f"Found new data with id: {id}")
                self.processed_ids.append(id)
                new_ids.append(id)

        if new_ids:
            with open("/app/data/processed_ids.txt", "w") as f:
                f.write("\n".join(self.processed_ids))
                logging.info("Updated the processed_ids.txt file")
        else:
            logging.info("Could not find new data")

        return new_ids 
    
    def send_next_queue(self, queue, data_folder):
        message_creator = messenger()
        message_creator.create_message_next_queue(queue, data_folder)

    def run_once(self):
        ids = self.Initiate_listener()
        folder_paths = [f"data/{id}" for id in ids]

        for path in folder_paths:
            if os.path.exists(path):
                self.send_next_queue(self.next_queue, path)
    
    def keep_running(self, interval=60):
        while True:
            logging.info("XNAT_listener is checking for new data in XNAT...")
            self.run_once()
            time.sleep(interval)

if __name__ == "__main__":
    engine = Runner()
    engine.keep_running()