import click
import json
import os
import time
import shutil
import socket
from datetime import datetime
import paho.mqtt.client as mqtt
from dateutil import parser


HOSTNAME = socket.gethostname()

@click.command()
@click.option(
    '-c', '--config_file',
    type=click.File('rb'),
    help='Sets the configuration file.',
    required=True,
)
def main(config_file):
    try:
        config = json.load(config_file)
        client = mqtt.Client()
        client.connect(config['broker_address'], port=int(config['broker_port']))
    except Exception as e:
        print(f'Error while opening file: {e}')
        exit(-1)
    start_time = datetime.utcnow()
    while True:
        files_to_process = os.listdir(config['source'])
        if not files_to_process:
            waiting = datetime.utcnow() - start_time
            if waiting.total_seconds() > config['wait_new_files']:
                print(f"Stoping main process, no new files")
                break
            time.sleep(1.0)
            continue
        start_time = datetime.utcnow()
        for file in files_to_process:
            try:
                print(f'Processing file {file}')
                logfile = open(
                    os.path.join(config['source'], file),
                    "r",
                )
                log_lines = logfile.readlines()
                for line in log_lines:
                    process_line(line, config, client)
                logfile.close()
                rotate_logfile(
                    os.path.join(config['source'], file),
                    file,
                    config['destination'],
                )
            except Exception:
                pass
    print("Done")


def rotate_logfile(file_location, file_name, destination):
    if not os.path.exists(destination):
        os.mkdir(destination)
    try:
        shutil.move(file_location, destination)
    except:
        shutil.move(
            file_location,
            destination + f"/{file_name}_" + str(int(datetime.timestamp(datetime.utcnow()))),
        )


def process_line(line, config, client):
    try:
        data = line.split(',')
        if 'CPU' in data[2] and data[3] == config['core']:
            data[0] = parser.parse(data[0]+'Z')
            line_protocol = (
                f"{config['measurement']},"
                f"hostname={HOSTNAME},CPU={data[2]},CORE={data[3] if data[3] else 'ALL'}"
                f" "
                f"CFreq={data[5]},"
                f"UFreq={data[6]},"
                f"PState={data[7]},"
                f"Util={data[8]},"
                f"IPC={data[9]},"
                f"Temp={data[13]},"
                f"DTS={data[14]},"
                f"Power={data[15]},"
                f"Volt={data[16]},"
                f"UVolt={data[17]},"
                f"TL={data[20]},"
                f"TMargin={data[21]}"
                f" {int(time.mktime(data[0].timetuple())*1e9)}"
            )
            print(line_protocol)
            send_line(line_protocol, config, client)
    except Exception as e:
        print(f"Skipped line {e}")


def send_line(line_protocol, config, client):
    try:
        client.publish(topic=config['broker_topic'], payload=line_protocol)
    except Exception as e:
        print(f"Error publishing to message broker: {e}")


if __name__ == '__main__':
    main()
