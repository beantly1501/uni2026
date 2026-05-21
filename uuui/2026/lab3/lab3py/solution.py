import sys
import math
from collections import Counter

class Node:
    def __init__(self):
        self.feature = None
        self.featureIndex = None
        self.children = {}
        self.label = None
        self.defaultLabel = None

class ID3:
    def __init__(self, maxDepth=None):
        self.maxDepth = maxDepth
        self.root = None
        self.headers = None
        self.labelIndex = None
        self.featuresDict = None

    def fit(self, headers, rows):
        self.headers = headers # like weather, temperature, ...
        self.labelIndex = len(headers) - 1 # index of the class labels
        self.featuresDict = {feat: index for index, feat in enumerate(headers[:-1])} # lookup dictionary, like {"weather": 0, "temperature": 1, ...}
        labels = [row[self.labelIndex] for row in rows] # collects all class labels, like yes or no

        self.root = id3(rows, self.featuresDict, self.labelIndex, self.maxDepth, 0, labels) # builds the decision tree and returns a node with all children

    # returns a list of predictions for the given rows
    def predict(self, rows):
        return [predictOne(self.root, row, self.headers) for row in rows]

def loadCsv(path):
    with open(path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]
    headers = lines[0].split(',')
    rows = [line.split(',') for line in lines[1:]]
    return headers, rows

# returns the majority label from the given list of labels, breaking ties alphabetically
def majorityLabel(labels):
    counts = Counter(labels)
    maxCount = max(counts.values())
    candidates = []
    for label, count in counts.items():
        if count == maxCount:
            candidates.append(label)
    candidates.sort()
    return candidates[0]

def entropy(labels):
    n = len(labels)
    if n == 0:
        return 0.0
    counts = Counter(labels)
    result = 0.0
    for c in counts.values():
        p = c / n
        result -= p * math.log2(p)
    return result

def informationGain(rows, featureIndex, labelIndex):
    labels = [row[labelIndex] for row in rows]
    baseEntropy = entropy(labels) # computes the base entropy of the full dataset

    n = len(rows)
    values = {} # creates buckets of class labels for each feature label (ex. temperature has high, med, low; buckets would be high: 2 yes, 3 no, ..)
    for row in rows:
        v = row[featureIndex] # value of the feature for this row
        if v not in values:
            values[v] = []
        values[v].append(row[labelIndex]) # we get the label of that row and add it to the feature label bucket

    weightedEntropy = 0.0
    for subsetLabels in values.values(): # compute the entropy for each group and sum them
        weightedEntropy += (len(subsetLabels) / n) * entropy(subsetLabels)
    return baseEntropy - weightedEntropy


def id3(rows, featuresDict, labelIndex, maxDepth, currentDepth, parentLabels):
    labels = [row[labelIndex] for row in rows]

    if not rows:
        return majorityLabel(parentLabels) if parentLabels else None

    default = majorityLabel(labels)

    # we use maxDepth to avoid overfitting
    if maxDepth is not None and currentDepth >= maxDepth:
        node = Node()
        node.label = default
        return node

    if len(set(labels)) == 1:
        node = Node()
        node.label = labels[0]
        return node

    if not featuresDict:
        node = Node()
        node.label = default
        return node

    gains = []
    for feat, index in featuresDict.items():
        ig = informationGain(rows, index, labelIndex)
        gains.append((ig, feat, index))

    gains.sort(key=lambda x: x[1]) # first, sort alphabetically by feature name for determinism
    gains.sort(key=lambda x: x[0], reverse=True) # then, sort by information gain in descending order
    bestIg, bestFeature, bestIndex = gains[0]

    node = Node()
    node.feature = bestFeature
    node.featureIndex = bestIndex
    node.defaultLabel = default

    remainingFeatures = {feat: index for feat, index in featuresDict.items() if feat != bestFeature} # features without the best feature

    # create buckets of rows for each value of the best feature
    values = {}
    for row in rows:
        v = row[bestIndex]
        if v not in values:
            values[v] = []
        values[v].append(row)

    # recursively build child nodes for each value of the best feature
    for v, subset in values.items():
        child = id3(subset, remainingFeatures, labelIndex, maxDepth, currentDepth + 1, labels)
        node.children[v] = child

    # final return will be the root node with all children attached
    return node

# used for printing the branches of the tree
def collectBranches(node, path):
    if node is None:
        return []
    if node.label is not None:
        fullPath = path + [node.label]
        return [fullPath]
    branches = []
    for v in sorted(node.children.keys()): # sorted feature values
        child = node.children[v]
        segment = f"{len(path) + 1}:{node.feature}={v}"
        extendedPath = path + [segment]
        branches.extend(collectBranches(child, extendedPath))
    return branches

# traverses through the tree to make a prediction for a single row
def predictOne(node, row, headers):
    if node is None:
        return None
    if node.label is not None:
        return node.label
    featIndex = node.featureIndex
    value = row[featIndex]
    if value in node.children:
        return predictOne(node.children[value], row, headers)
    else:
        return node.defaultLabel

def main():
    trainPath = sys.argv[1]
    testPath = sys.argv[2]
    maxDepth = int(sys.argv[3]) if len(sys.argv) > 3 else None

    trainHeaders, trainRows = loadCsv(trainPath)
    testHeaders, testRows = loadCsv(testPath)

    model = ID3(maxDepth=maxDepth)
    model.fit(trainHeaders, trainRows)

    branches = collectBranches(model.root, [])
    print("[BRANCHES]:")
    for branch in branches:
        print(' '.join(branch))

    predictions = model.predict(testRows)
    print("[PREDICTIONS]: " + ' '.join(predictions))

    labelIndex = len(testHeaders) - 1
    trueLabels = [row[labelIndex] for row in testRows] # collects the true class labels from the testCsv

    correct = sum(1 for true, prediction in zip(trueLabels, predictions) if true == prediction) # sums up the number of correct predictions
    accuracy = correct / len(trueLabels)
    print(f"[ACCURACY]: {accuracy:.5f}")

    # confusion matrix
    allLabels = sorted(set(trueLabels) | set(predictions)) # all unique labels
    labelToIndex = {label: i for i, label in enumerate(allLabels)} # mapping labels to indexes, like no: 0, yes: 1
    size = len(allLabels)

    matrix = []
    for _ in range(size):
        matrix.append([0] * size)

    # uses labelToIndex to find the correct row and column for the true label and predicted label, and then increments that number in the matrix
    for trueLabel, predicted in zip(trueLabels, predictions):
        rowIndex = labelToIndex[trueLabel]
        colIndex = labelToIndex[predicted]
        matrix[rowIndex][colIndex] += 1

    print("[CONFUSION_MATRIX]:")
    for row in matrix:
        rowAsStrings = [str(count) for count in row]
        print(' '.join(rowAsStrings))


if __name__ == '__main__':
    main()
