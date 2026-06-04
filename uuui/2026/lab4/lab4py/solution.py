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

def calculateFitness(mse):
    return 1.0 / (1.0 + mse)

def selectParent(population):
    fitnessSum = sum(chrom.fitness for chrom in population)
    probabilities = [chrom.fitness / fitnessSum for chrom in population]
    return np.random.choice(population, p=probabilities)

def crossover(parent1, parent2, architecture):
    childParams = (parent1.getArrayOfParams() + parent2.getArrayOfParams()) / 2
    child = NeuralNetwork(parent1.weights[0].shape[0], architecture)
    child.setParamsFromArray(childParams)
    return child

def mutate(chromosome, mutationProb, mutationScale):
    params = chromosome.getArrayOfParams()
    for i in range(len(params)):
        if np.random.rand() < mutationProb:
            params[i] += np.random.normal(0, mutationScale)
    chromosome.setParamsFromArray(params)
    return chromosome

class NeuralNetwork:
    def __init__(self, inputsSize, architecture):
        self.layers = parseArchitecture(architecture)
        self.weights = []
        self.biases = []
        self.fitness = 0.0

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
    
    def meanSquaredError(self, inputs, correctValues):
        prediction = self.forwardPass(inputs)

        return np.mean((correctValues - prediction) ** 2)
    
    def setParamsFromArray(self, params):
        index = 0
        for layerIndex in range(len(self.weights)):
            w = self.weights[layerIndex]
            self.weights[layerIndex] = params[index : index + w.size].reshape(w.shape)
            index += w.size

            b = self.biases[layerIndex]
            self.biases[layerIndex] = params[index : index + b.size].reshape(b.shape)
            index += b.size

    def getArrayOfParams(self):
        params = []
        for w, b in zip(self.weights, self.biases):
            params.append(w.flatten())
            params.append(b.flatten())
        return np.concatenate(params)
        
def geneticAlgorithm(inputsTrain, outputTrain, architecture, populationSize, elitismAmount, numIterations,
                     mutationProb, mutationScale, inputsTest, outputTest):
    population = [NeuralNetwork(inputsSize=inputsTrain.shape[1], architecture=architecture) for _ in range(populationSize)]
    newGeneration = []

    # evaluating fitness for population
    for chrom in population:
        chrom.forwardPass(inputsTrain)
        error = chrom.meanSquaredError(inputsTrain, outputTrain)
        chrom.fitness = calculateFitness(error)

    for generation in range(1, numIterations + 1):
        # evaluating eliteness
        orderedFitness = sorted(population, key=lambda chrom: chrom.fitness, reverse=True)

        if generation % 2000 == 0:
            bestChromosome = orderedFitness[0]
            print(f'[Train error @{generation}]: {bestChromosome.meanSquaredError(inputsTrain, outputTrain):.6f}')

        newGeneration = orderedFitness[:elitismAmount]

        while len(newGeneration) < populationSize:
            parent1 = selectParent(population)
            parent2 = selectParent(population)

            # crossover and mutation
            child = crossover(parent1, parent2, architecture)
            child = mutate(child, mutationProb, mutationScale)
            child.fitness = calculateFitness(child.meanSquaredError(inputsTrain, outputTrain))
            newGeneration.append(child)

        population = newGeneration

    bestChromosome = orderedFitness[0]
    print(f'[Test error]: {bestChromosome.meanSquaredError(inputsTest, outputTest):.6f}')
    

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--train', required=True)
    parser.add_argument('--test', required=True)
    parser.add_argument('--nn', required=True)
    parser.add_argument('--popsize', type=int, required=True)
    parser.add_argument('--elitism', type=int, required=True)
    parser.add_argument('--p', type=float, required=True)
    parser.add_argument('--K', type=float, required=True)
    parser.add_argument('--iter', type=int, required=True)

    args = parser.parse_args()

    inputsTrain, outputTrain = loadData(args.train)
    inputsTest, outputTest = loadData(args.test)

    geneticAlgorithm(inputsTrain=inputsTrain, outputTrain=outputTrain, architecture=args.nn, populationSize=args.popsize,
                     elitismAmount=args.elitism, numIterations=args.iter, mutationProb=args.p, 
                     mutationScale=args.K, inputsTest=inputsTest, outputTest=outputTest)

if __name__ == '__main__':
    main()