from hashlib import sha256
import json
import time
import argparse

from flask import Flask, request
import requests


class Block:
    def __init__(self, index, transactions, timestamp, previous_hash, nonce=0):
        self.index = index
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.nonce = nonce

    def compute_hash(self):
        block_string = json.dumps(self.__dict__, sort_keys=True)
        return sha256(block_string.encode()).hexdigest()


class Blockchain:
    PoW_difficulty = 1 # difficulty of our PoW algorithm

    def __init__(self):
        self.unconfirmed_transactions = []
        self.chain = []

    def create_genesis_block(self):
        genesis_block = Block(0, [], 0, "0")
        genesis_block.hash = genesis_block.compute_hash()
        self.chain.append(genesis_block)

    @property
    def last_block(self):
        return self.chain[-1]

    def add_block(self, block, proof):
        previous_hash = self.last_block.hash

        if previous_hash != block.previous_hash:
            return False

        if not Blockchain.is_valid_proof(block, proof):
            return False

        block.hash = proof
        self.chain.append(block)
        return True

    @staticmethod
    def proof_of_work(block):
        block.nonce = 0

        computed_hash = block.compute_hash()
        while not computed_hash.startswith('0' * Blockchain.PoW_difficulty):
            block.nonce += 1
            computed_hash = block.compute_hash()

        return computed_hash

    def add_new_transaction(self, transaction):
        self.unconfirmed_transactions.append(transaction)

    @classmethod
    def is_valid_proof(cls, block, block_hash):
        return (block_hash.startswith('0' * Blockchain.PoW_difficulty) and block_hash == block.compute_hash())

    @classmethod
    def check_chain_validity(cls, chain):
        result = True
        previous_hash = "0"

        for block in chain:
            block_hash = block.hash
            delattr(block, "hash")

            if not cls.is_valid_proof(block, block_hash) or previous_hash != block.previous_hash:
                result = False
                break

            block.hash, previous_hash = block_hash, block_hash

        return result

    def mine(self):
        if not self.unconfirmed_transactions:
            return False

        last_block = self.last_block

        new_block = Block(index=last_block.index + 1,
                          transactions=self.unconfirmed_transactions,
                          timestamp=time.time(),
                          previous_hash=last_block.hash)

        proof = self.proof_of_work(new_block)
        self.add_block(new_block, proof)

        self.unconfirmed_transactions = []

        return True


app = Flask(__name__)

blockchain = Blockchain()
blockchain.create_genesis_block()

peers = set()
PoS_name = "PoS1"
PoS_type = "Cash_Card"

@app.route('/new_transaction', methods=['POST'])
def new_transaction():
    tx_data = request.get_json()

    valid_card_no = True
    if tx_data["type"] != 'purchase':
        valid_card_no = False
        for block in blockchain.chain:
            txs = block.transactions
            for tx in txs:
                if tx_data["card"] == tx["card"]:
                    valid_card_no = True
                    break

    if not valid_card_no:
        tx_data["amount"] = "-1";
        return "Invalid card number " + tx_data["card"], 404

    tx_data["timestamp"] = time.time()

    if tx_data["type"] == 'balance':
        amount = -1
        for block in blockchain.chain:
            txs = block.transactions
            for tx in txs:
                if(tx["card"] == tx_data["card"]):
                    if tx["type"] == "purchase":
                        amount = 0
                    elif tx["type"] == "recharge":
                        amount += int(tx["amount"])
                    elif tx["type"] == "buy":
                        amount -= int(tx["amount"])
        tx_data["amount"] = str(amount)
        return json.dumps(tx_data)

    if tx_data["type"] == 'purchase':
        card_no = 0
        for block in blockchain.chain:
            txs = block.transactions
            for tx in txs:
                if card_no < int(tx["card"]):
                    card_no = int(tx["card"]) + 1
        tx_data["card"] = str(card_no)

    blockchain.add_new_transaction(tx_data)
    return json.dumps(tx_data)


@app.route('/chain', methods=['GET'])
def get_chain():
    chain_data = []
    for block in blockchain.chain:
        chain_data.append(block.__dict__)
    return json.dumps({"length": len(chain_data), "chain": chain_data, "peers": list(peers)})


@app.route('/mine', methods=['GET'])
def mine_unconfirmed_transactions():
    result = blockchain.mine()
    if not result:
        return "No transactions to mine"
    else:
        # Making sure we have the longest chain before announcing to the network
        chain_length = len(blockchain.chain)
        consensus()
        if chain_length == len(blockchain.chain):
            # announce the recently mined block to the network
            announce_new_block(blockchain.last_block)
        return "Block #{} is mined.".format(blockchain.last_block.index)

@app.route('/register_node', methods=['POST'])
def register_new_peers():
    node_address = request.get_json()["node_address"]
    if not node_address:
        return "Invalid data", 400

    peers.add(node_address)

    return get_chain()


@app.route('/register_with', methods=['POST'])
def register_with_existing_node():
    node_address = request.get_json()["node_address"]
    if not node_address:
        return "Invalid data", 400

    data = {"node_address": request.host_url}
    headers = {'Content-Type': "application/json"}

    response = requests.post(node_address + "/register_node", data=json.dumps(data), headers=headers)

    if response.status_code == 200:
        global blockchain
        global peers
        chain_dump = response.json()['chain']
        blockchain = create_chain_from_dump(chain_dump)
        peers.update(response.json()['peers'])
        return "Registration successful", 200
    else:
        return response.content, response.status_code


def create_chain_from_dump(chain_dump):
    generated_blockchain = Blockchain()
    generated_blockchain.create_genesis_block()
    for idx, block_data in enumerate(chain_dump):
        if idx == 0:
            continue  # skip genesis block
        block = Block(block_data["index"],
                      block_data["transactions"],
                      block_data["timestamp"],
                      block_data["previous_hash"],
                      block_data["nonce"])
        proof = block_data['hash']
        added = generated_blockchain.add_block(block, proof)
        if not added:
            raise Exception("The chain dump is tampered!!")
    return generated_blockchain


@app.route('/add_block', methods=['POST'])
def verify_and_add_block():
    block_data = request.get_json()
    block = Block(block_data["index"],
                  block_data["transactions"],
                  block_data["timestamp"],
                  block_data["previous_hash"],
                  block_data["nonce"])

    proof = block_data['hash']
    added = blockchain.add_block(block, proof)

    if not added:
        return "The block was discarded by the node", 400

    return "Block added to the chain", 201

@app.route('/pending_tx', methods=['GET'])
def get_pending_tx():
    return json.dumps(blockchain.unconfirmed_transactions)

@app.route('/pos_name', methods=['GET'])
def get_pos_name():
    return json.dumps(PoS_name)

@app.route('/pos_type', methods=['GET'])
def get_pos_type():
    return json.dumps(PoS_type)

def consensus():
    global blockchain

    longest_chain = None
    current_len = len(blockchain.chain)

    for node in peers:
        response = requests.get('{}chain'.format(node))
        length = response.json()['length']
        chain = response.json()['chain']
        if length > current_len and blockchain.check_chain_validity(chain):
            current_len = length
            longest_chain = chain

    if longest_chain:
        blockchain = longest_chain
        return True

    return False


def announce_new_block(block):
    for peer in peers:
        url = "{}add_block".format(peer)
        headers = {'Content-Type': "application/json"}
        requests.post(url, data=json.dumps(block.__dict__, sort_keys=True), headers=headers)

def main():
  global PoS_name
  global PoS_type
  parser = argparse.ArgumentParser()
  parser.add_argument("-p", "--port", help = "Port number")
  parser.add_argument("-n", "--name", help = "PoS name")
  parser.add_argument("-t", "--type", help = "PoS type: c-Cash_Card or r-Retail")

  args = parser.parse_args()

  PoS_name = args.name
  if(args.type == 'c'):
    PoS_type = 'Cash_Card'
  else:
    PoS_type = 'Retail'
  app.run(debug=False, port=args.port)
  return 0

if __name__ == "__main__":
  main()
