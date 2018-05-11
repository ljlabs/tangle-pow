import properties as prop
import json
from time import time
import hashlib
import requests
from urllib.parse import urlparse


"""
nodes in the dag are represented in json as folows
they can be transmitted across the network in this form and then can be
initialized in this form
        Node = {
            'index': "int value",
            'timestamp': time(),
            'data': "this is the transaction data that is being stored",
            'proof': "proof of work",
            'previous_hashs': "the hash of the previous 2 nodes that it is connected to",
            'previous_nodes': 'index values',
            'next_nodes': 'indexes of the nodes pointing to it',
            'validity': the number of times the node has been proven
        }

"""

class Tangle(object):
    def __init__(self):
        self.nodes = []
        self.peers = set()
        for i in range(prop.numberOfValidationNodesNeeded):
            # Create the genesis block
            self.nodes.append(self.createNode(None, [], len(self.nodes), validity = prop.RequiredProofs))

    @staticmethod
    def valid_proof(last_proof, last_hash, proof):
        # ensures that the node has the correct number of zeros

        guess = (str(last_proof) + str(last_hash) + str(proof)).encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"

    def proof_of_work(self, last_proof, last_hash):
        # computes the proof of work
        proof = 0
        while self.valid_proof(last_proof, last_hash, proof) is False:
            proof += 1
        return proof


    @staticmethod
    def hash(node):
        # make a hash of the block
        # We must make sure that the Dictionary is Ordered, or we'll have inconsistent hashes
        node_string = json.dumps(node, sort_keys=True).encode()
        return hashlib.sha256(node_string).hexdigest()

    def validate_node(self, node):
        if self.nodes[node['index']]['validity'] < prop.RequiredProofs:
            last_proof = self.nodes[node['index']]['proof'] # this nodes proof
            last_hash = ""
            for prevHash in self.nodes[node['index']]['previous_hashs']:
                last_hash += prevHash # the hashes of the nodes this node connects
            self.nodes[node['index']]['proof'] = self.proof_of_work(last_proof, last_hash)
            self.nodes[node['index']]['validity'] += 1

    def createNode(self, data, prevNodes, newIndex, validity=0):# these prevNodes are the indexes in the dag that points to the previous nodes
        prevHashes = []
        '''
        may need to update every node that points to this when sending transaction
        '''
        for i in prevNodes:
            prevHashes.append(self.hash(self.nodes[i]))
            # now we tell the nodes that we are pointing to that we are poiinting to them
            self.nodes[i]['next_nodes'].append(newIndex)

        Node = {
            'index': newIndex,
            'timestamp': time(),
            'data': data,
            'proof': 0,
            'previous_hashs': prevHashes,          # hashes of the nodes we are connecting to
            'previous_nodes': prevNodes,                # indexes of the nodes we are connecting to
            'next_nodes': [],                           # indexes of future nodes that will connect to us
            'validity': validity,
        }
        return Node


    def send_transaction(self, data):
        # find 2 nodes in the network that are un proven
        nodesToattach = []
        nodesIndexes = []
        newIndex = len(self.nodes)
        worstCaseScinario = []
        worstCaseScinarioindexes = []
        '''
        this function should be changed to search randomly
        '''
        for i in range(len(self.nodes)-1, -1, -1):
            node=self.nodes[i]
            if node['validity'] < prop.RequiredProofs:
                nodesToattach.append(node)
                nodesIndexes.append(node['index'])
            else:
                if worstCaseScinario == [] or len(worstCaseScinario) < prop.numberOfValidationNodesNeeded:
                    worstCaseScinario.append(node)
                    worstCaseScinarioindexes.append(node['index'])
            if len(nodesToattach) == prop.numberOfValidationNodesNeeded:
                break
        # if there are not enough un varified transactions then use verified transactions
        while len(nodesToattach) < prop.numberOfValidationNodesNeeded:
            nodesToattach.append(worstCaseScinario.pop())
            nodesIndexes.append(worstCaseScinarioindexes.pop())
        # process nodes to attatch
        for node in nodesToattach:
            self.validate_node(node)
        # now that those nodes are proven
        # we can now attatch our node to the dag
        self.nodes.append(self.createNode(data, nodesIndexes, newIndex))
        return newIndex


    ###########################################################################
    # this is the consensus algorithm
    ###########################################################################

    def valid_tangle(self, tangle):
        for node in tangle:
            if node['index'] >= prop.numberOfValidationNodesNeeded: # dont test genesis nodes
                validitiyOfNode = node['validity']
                # make sure that the same number of nodes saying that they have
                # validated him as his validity level
                nextNodes = node['next_nodes']
                print(nextNodes)
                if validitiyOfNode < len(nextNodes):
                    return False
                # make sure these nodes are pointing to him
                for Nnode in nextNodes:
                    print(tangle[Nnode])
                    if node['index'] not in tangle[Nnode]['previous_nodes']:
                        return False
        return True

    def register_peer(self, address):
        parsed_url = urlparse(address)
        self.peers.add(parsed_url.netloc)

    def resolve_conflicts(self):
        neighbours = self.peers
        new_tangle = None

        # We're only looking for chains longer than ours
        max_length = len(self.nodes)

        # Grab and verify the chains from all the peers in our network
        for peer in neighbours:
            response = requests.get("http://"+str(peer) + "/tangle")

            if response.status_code == 200:
                length = response.json()['length']
                tangle = response.json()['tangle']

                # Check if the length is longer and the chain is valid
                if length > max_length and self.valid_tangle(tangle):
                    max_length = length
                    new_tangle = tangle

        # Replace our chain if we discovered a new, valid chain longer than ours
        if new_tangle:
            self.nodes = new_tangle
            return True

        return False
