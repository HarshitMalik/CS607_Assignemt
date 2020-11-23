import datetime
import json
import subprocess
import os

import requests
from flask import render_template, redirect, request

from app import app

# The node with which our application interacts, there can be multiple
# such nodes as well.
NODE_ADDRESS = "http://127.0.0.1:"
available_port = 8000
PoS_nodes = []
posts = []

class PoS():
    def __init__(self, name,type,port,process):
        self.name = name
        self.type = type
        self.port = port
        self.process = process
    def stop(self):
        self.process.kill()

@app.route('/PoS/<string:PoS_name>/mine')
def request_mine(PoS_name):
    global PoS_nodes
    for node in PoS_nodes:
        if node.name == PoS_name:
            address = NODE_ADDRESS + str(node.port)

    get_chain_address = "{}/mine".format(address)
    response = requests.get(get_chain_address)
    return response.text

@app.route('/PoS/<string:PoS_name>/chain')
def get_pos_blockchain(PoS_name):
    global PoS_nodes
    for node in PoS_nodes:
        if node.name == PoS_name:
            address = NODE_ADDRESS + str(node.port)

    get_chain_address = "{}/chain".format(address)
    response = requests.get(get_chain_address)
    if response.status_code == 200:
        chain = json.loads(response.content)
        return chain

    return "Operation Failed"


@app.route('/')
def index():
    #fetch_posts()
    return render_template('index.html', PoS_nodes= PoS_nodes, readable_time=timestamp_to_string)


@app.route('/add_pos', methods=['POST'])
def add_pos_terminal():
    global available_port
    global PoS_nodes
    PoS_name = request.form["PoS_name"]
    PoS_type = request.form["PoS_type"]

    cwd = os.getcwd()
    sp = subprocess.Popen("python3 " +cwd+"/node_server.py -p " +str(available_port) +" -n "+ str(PoS_name) + " -t " + PoS_type, shell=True)
    new_PoS_node = PoS(PoS_name,PoS_type,available_port,sp)
    PoS_nodes.append(new_PoS_node)

    if available_port > 8000:
        data = {
            "node_address": NODE_ADDRESS+"8000",
        }

        # Submit a transaction
        register_address = "{}/register_with".format(NODE_ADDRESS+str(available_port))
        response = requests.post(new_tx_address, json=data, headers={'Content-type': 'application/json'})
        if response.status_code != 200:
            print("Error in registering new node -",response.text)
    available_port += 1
    return redirect('/')

@app.route('/remove_pos', methods=['POST'])
def remove_pos_terminal():
    global PoS_nodes
    PoS_port = request.form["PoS_port"]
    for idx, node in enumerate(PoS_nodes):
        if node.port == PoS_port:
            node.stop()
            PoS_nodes.pop(idx)
            break
    return redirect('/')

@app.route('/remove_all_pos')
def remove_all_pos_terminal():
    global PoS_nodes
    for node in PoS_nodes:
        node.stop()

    PoS = []
    available_port = 8000
    return redirect('/')

@app.route('/PoS/<string:PoS_name>')
def interact_with_pos(PoS_name):
    global PoS_nodes
    for node in PoS_nodes:
        if node.name == PoS_name:
            if node.type == 'c':
                return render_template('pos_c.html', PoS_node= node, readable_time=timestamp_to_string)
            return render_template('pos_r.html', PoS_node= node, readable_time=timestamp_to_string)
    return redirect('/')

@app.route('/PoS/<string:PoS_name>/purchase')
def purchase_card(PoS_name):
    global PoS_nodes

    for node in PoS_nodes:
        if node.name == PoS_name:
            address = NODE_ADDRESS + str(node.port)
            break

    tx_object = {
        "card": "-1",
        "amount": "0",
        "type" : "purchase"
    }

    # Submit a transaction
    new_tx_address = "{}/new_transaction".format(address)
    response = requests.post(new_tx_address, json=tx_object, headers={'Content-type': 'application/json'})
    card_no = -1
    if response.status_code == 200:
        tx = json.loads(response.content)
        card_no = int(tx["card"])
    return str(card_no)

    return redirect('/')


@app.route('/PoS/<string:PoS_name>/balance', methods=['POST'])
def check_balance(PoS_name):
    global PoS_nodes

    card_no = request.form["card_no"]

    for node in PoS_nodes:
        if node.name == PoS_name:
            address = NODE_ADDRESS + str(node.port)
            break

    tx_object = {
        'card': str(card_no),
        'amount': "0",
        'type' : "balance"
    }

    # Submit a transaction
    new_tx_address = "{}/new_transaction".format(address)

    response = requests.post(new_tx_address, json=tx_object, headers={'Content-type': 'application/json'})
    balance = -2
    if response.status_code == 200:
        tx = json.loads(response.content)
        balance = int(tx["amount"])
    return str(balance)
    return redirect('/')

@app.route('/PoS/<string:PoS_name>/recharge', methods=['POST'])
def recharge_card(PoS_name):
    global PoS_nodes

    card_no = request.form["card_no"]
    amount = request.form["amount"]

    for node in PoS_nodes:
        if node.name == PoS_name:
            address = NODE_ADDRESS + str(node.port)
            break

    tx_object = {
        'card': str(card_no),
        'amount': str(amount),
        'type' : "recharge"
    }

    # Submit a transaction
    new_tx_address = "{}/new_transaction".format(address)

    response = requests.post(new_tx_address, json=tx_object, headers={'Content-type': 'application/json'})
    print("MEESAGE",response.text)
    balance = -2
    if response.status_code == 200:
        tx = json.loads(response.content)
        balance = int(tx["amount"])
    return str(balance)

    return redirect('/')

@app.route('/PoS/<string:PoS_name>/buy', methods=['POST'])
def buy_items(PoS_name):
    global PoS_nodes

    card_no = request.form["card_no"]
    amount = request.form["amount"]

    for node in PoS_nodes:
        if node.name == PoS_name:
            address = NODE_ADDRESS + str(node.port)
            break

    tx_object = {
        'card': str(card_no),
        'amount': dtr(amount),
        'type' : "buy"
    }

    # Submit a transaction
    new_tx_address = "{}/new_transaction".format(address)

    response = requests.post(new_tx_address, json=tx_object, headers={'Content-type': 'application/json'})
    balance = -2
    if response.status_code == 200:
        tx = json.loads(response.content)
        balance = int(tx["amount"])
    return str(balance)
    return redirect('/')


def timestamp_to_string(epoch_time):
    return datetime.datetime.fromtimestamp(epoch_time).strftime('%H:%M')
