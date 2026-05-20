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
        self.headers = headers
        self.labelIndex = len(headers) - 1
        self.featuresDict = {feat: index for index, feat in enumerate(headers[:-1])}
        labels = [row[self.labelIndex] for row in rows]

        self.root = id3(rows, self.featuresDict, self.labelIndex, self.maxDepth, 0, labels)

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
    baseEntropy = entropy(labels)

    n = len(rows)
    values = {}
    for row in rows:
        v = row[featureIndex]
        if v not in values:
            values[v] = []
        values[v].append(row[labelIndex])

    weightedEntropy = 0.0
    for subsetLabels in values.values():
        weightedEntropy += (len(subsetLabels) / n) * entropy(subsetLabels)
    return baseEntropy - weightedEntropy


def id3(rows, featuresDict, labelIndex, maxDepth, currentDepth, parentLabels):
    labels = [row[labelIndex] for row in rows]

    if not rows:
        return majorityLabel(parentLabels) if parentLabels else None

    default = majorityLabel(labels)

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

    gains.sort(key=lambda x: x[1])
    gains.sort(key=lambda x: x[0], reverse=True)
    bestIg, bestFeature, bestIndex = gains[0]

    node = Node()
    node.feature = bestFeature
    node.featureIndex = bestIndex
    node.defaultLabel = default

    remainingFeatures = {feat: index for feat, index in featuresDict.items() if feat != bestFeature}

    values = {}
    for row in rows:
        v = row[bestIndex]
        if v not in values:
            values[v] = []
        values[v].append(row)

    for v, subset in values.items():
        child = id3(subset, remainingFeatures, labelIndex, maxDepth, currentDepth + 1, labels)
        node.children[v] = child

    return node

# used for printing the branches of the tree
def collectBranches(node, path):
    if node is None:
        return []
    if node.label is not None:
        fullPath = path + [node.label]
        return [fullPath]
    branches = []
    for v in sorted(node.children.keys()):
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
    trueLabels = [row[labelIndex] for row in testRows]

    correct = sum(1 for true, prediction in zip(trueLabels, predictions) if true == prediction)
    accuracy = correct / len(trueLabels)
    print(f"[ACCURACY]: {accuracy:.5f}")

if __name__ == '__main__':
    main()
