import csv
import numpy as np
import argparse

def loadData(path):
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader) # skip header
        data = np.array(list(reader), dtype=float)
    inputs = data[:, :-1]
    target   = data[:, -1:]
    return np.array(inputs), np.array(target)

def parseArchitecture(config):
    layers = []
    element = ''
    for c in config:
        if c.isdigit():
            element += c
        elif c == 's':
            layers.append(int(element))

    return layers

def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))

class NeuralNetwork:
    def __init__(self, inputsSize, architecture):
        self.layers = parseArchitecture(architecture)
        self.weights = []
        self.biases = []

        inputs = inputsSize
        for layerSize in self.layers:
            self.weights.append(np.random.normal(0, 0.01, (inputs, layerSize)))
            self.biases.append(np.random.normal(0, 0.01, (1, layerSize)))

            inputs = layerSize

        self.weights.append(np.random.normal(0, 0.01, (inputs, 1)))
        self.biases.append(np.random.normal(0, 0.01, (1, 1)))

    def forwardPass(self, inputs):
        calculatedHidden = inputs
        for layer in range(len(self.layers)):
            calculatedHidden = np.dot(calculatedHidden, self.weights[layer]) + self.biases[layer]
            
            for z in range(calculatedHidden.shape[1]):
                calculatedHidden[:, z] = sigmoid(calculatedHidden[:, z])

        return np.dot(calculatedHidden, self.weights[-1]) + self.biases[-1]
    

        




def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--train', required=True)
    parser.add_argument('--nn', required=True)

    args = parser.parse_args()

    inputsTrain, outputTrain = loadData(args.train)

    neuralNetwork = NeuralNetwork(inputsSize=inputsTrain.shape[1], architecture=args.nn)

if __name__ == '__main__':
    main()

