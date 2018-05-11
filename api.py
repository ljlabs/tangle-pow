import hashlib
import json
from textwrap import dedent
from time import time
from uuid import uuid4
from tangle import Tangle
from urllib.parse import urlparse

import requests
from flask import Flask, jsonify, request

# Instantiate our Node
app = Flask(__name__)

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

# Instantiate the Blockchain
tangle = Tangle()



@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    # update tangle
    tangle.resolve_conflicts()
    # begin transaction
    values = request.get_json()

    # Check that the required fields are in the POST'ed data
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # Create a new Transaction
    index = tangle.send_transaction(values)

    response = {'message': 'Transaction will be added to Block ' + str(index)}
    # tell peers to update tangle
    for peer in tangle.peers:
        requests.get("http://"+str(peer) + "/peers/resolve")
    return jsonify(response), 201

@app.route('/tangle', methods=['GET'])
def full_chain():
    response = {
        'tangle': tangle.nodes,
        'length': len(tangle.nodes),
    }
    return jsonify(response), 200

# Consensus


@app.route('/peers/register', methods=['POST'])
def register_nodes():
    values = request.get_json()
    print(values)
    print("asdugdag")
    peers = None
    if type("") == type(values):
        print(json.loads(values))
        peers = json.loads(values)['peers']
    else:
        peers = values.get('peers')
    if peers is None:
        return "Error: Please supply a valid list of nodes", 400

    for peer in peers:
        tangle.register_peer(peer)


    response = {
        'message': 'New peers have been added',
        'total_nodes': list(tangle.peers),
    }

    return jsonify(response), 201

@app.route('/peers/resolve', methods=['GET'])
def consensus():
    replaced = tangle.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': tangle.nodes
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': tangle.nodes
        }

    return jsonify(response), 200




@app.route('/peers', methods=['GET'])
def list_peers():
    response = {
        'known_peers': list(tangle.peers),
    }

    return jsonify(response), 201







if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
