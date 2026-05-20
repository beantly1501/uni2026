import sys
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
        pass

    def predict(self, rows):
        pass

def loadCsv(path):
    with open(path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]
    headers = lines[0].split(',')
    rows = [line.split(',') for line in lines[1:]]
    return headers, rows

def main():
    trainPath = sys.argv[1]
    testPath = sys.argv[2]
    maxDepth = int(sys.argv[3]) if len(sys.argv) > 3 else None

    trainHeaders, trainRows = loadCsv(trainPath)
    testHeaders, testRows = loadCsv(testPath)

if __name__ == '__main__':
    main()
