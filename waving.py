import paho.mqtt.client as mqtt
import pigpio
from time import sleep
import time  # Ensure time is imported
import ssl
import logging

# Set up basic logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Flag to track cooldown and time of last action
waving = False
last_wave_time = 0  # Store timestamp of last wave command
TIMEOUT = 5  # Timeout period in seconds (change to 5 seconds)

# Define logging for MQTT
def on_log(client, userdata, level, buf):
    """This function logs all MQTT messages."""
    logging.debug(f"MQTT Log - Level: {level}, Message: {buf}")

# Initialize pigpio
pi = pigpio.pi()

# GPIO setup
SERVO_PIN = 4  # Replace with your GPIO pin

# MQTT setup
MQTT_BROKER = "192.168.0.171"  # Replace with your MQTT broker address
MQTT_TOPIC = "servo/controls"  # Replace with your desired topic

# Function to move the servo
def move_servo():
    try:
        logging.info("Moving servo clockwise")
        pi.set_servo_pulsewidth(SERVO_PIN, 2000)  # Clockwise (increase pulse width for clockwise)
        sleep(0.5)

        logging.info("Returning servo to neutral")
        pi.set_servo_pulsewidth(SERVO_PIN, 1500)  # Neutral position (1500 is usually neutral)
        sleep(0.5)

    except Exception as e:
        logging.error(f"Error moving servo: {e}")

# MQTT callbacks
def on_connect(client, userdata, flags, rc):
    logging.info(f"Connected with result code {rc}")
    if rc == 0:
        client.subscribe(MQTT_TOPIC)
    else:
        logging.warning(f"Failed to connect with code {rc}")

def on_message(client, userdata, msg):
    global waving, last_wave_time  # Declare waving and last_wave_time as global to modify them inside the function

    logging.info(f"Received message on topic {msg.topic}: {msg.payload.decode('utf-8')}")
    if msg.topic == MQTT_TOPIC:
        command = msg.payload.decode("utf-8")
        logging.info(f"Command received: {command}")

        # Get the current time
        current_time = time.time()

        # Check if cooldown period has passed and if we're allowed to process the command
        if command == "move_servo" and time.time() - last_wave_time >= TIMEOUT:
            logging.info("Processing 'move_servo' command...")
            waving = True  # Start cooldown
            move_servo()  # Actually move the servo
            last_wave_time = current_time  # Update the last wave time after processing the command
            logging.info("Cooldown started, waiting for 5 seconds.")
            waving = False  # Reset waving flag after cooldown period
        elif command == "move_servo" and time.time() - last_wave_time < TIMEOUT:
            logging.info("Command discarded due to cooldown.")  # Log when command is discarded
        else:
            logging.info("Invalid command or no action needed.")
            # finished moving servo

# MQTT client setup
client = mqtt.Client(transport="websockets") #sets the client connection to websockets!!!!
ca_certs = "/etc/ssl/certs/ISRG_Root_X1.pem"
client.on_log = on_log  # Enable MQTT logging

# Set the TLS/SSL parameters for the client
client.tls_set(
    ca_certs=ca_certs,
    cert_reqs=ssl.CERT_REQUIRED,
    tls_version=ssl.PROTOCOL_TLS_CLIENT
)
client.tls_insecure_set(False) # sets the tls to secure

client.username_pw_set(username="test", password="test") # uses the username test and the passwd test

client.on_message = on_message # when a message gets recieved

client.connect('clawclan.co.uk', 19132) # connects to the mqtt server

client.subscribe(MQTT_TOPIC) # subscribes to the servo/controls topic

# Start MQTT loop yes
try:
    client.loop_start()
    logging.info("Listening for MQTT commands...")
    while True:
        sleep(1)
except KeyboardInterrupt:
    logging.info("Exiting gracefully...")
except Exception as e:
    logging.error(f"Unexpected error: {e}")
finally:
    logging.info("Disconnecting MQTT client...")
    pi.set_servo_pulsewidth(SERVO_PIN, 0)  # Turn off the servo
    pi.stop()  # Stop pigpio
    client.loop_stop()
    client.disconnect()
