from __future__ import annotations
import argparse
import os

class Node:
    def __init__(self, name: str, distance: float, parent: Node | None = None, heuristic: int = 0):
        self.name = name
        self.distance = distance
        self.heuristic = heuristic
        self.parent = parent

    def __str__(self):
        return f"Node({self.name}, {self.distance})"

    def __repr__(self):
        return f"Node({self.name}, {self.distance})"


def dataLoading(stateSpaceFile, heuristicsFile=None):

    stateSpace: dict[str, list[Node]] = dict()

    # with heuristics file
    if heuristicsFile:
        heuristicsNameValues: dict[str, float] = dict()

        with open(heuristicsFile) as f:
            lines = f.readlines()

            strippedLines: list[str] = list()

            for line in lines:
                if line.startswith("#"):
                    continue
                else:
                    line = line.strip()
                    line = line.rstrip("\n")
                    strippedLines.append(line)
            
            for line in strippedLines:
                splitLines = line.split(" ")

                nodeName = splitLines[0].rstrip(":")
                nodeValue = splitLines[1]

                heuristicsNameValues[nodeName] = nodeValue

        with open(stateSpaceFile) as f:
            lines = f.readlines()

            strippedLines: list[str] = list()

            for line in lines:
                if line.startswith("#"):
                    continue
                else:
                    line = line.strip()
                    line = line.rstrip('\n')
                    strippedLines.append(line)

            for line in strippedLines[2:]:
                splitLines = line.split()

                keyNode = splitLines[0].rstrip(':')
                nodeValues: list[Node] = list()

                for splitLine in splitLines[1:]:
                    splitNode = splitLine.split(',')
                    newNode = Node(name = splitNode[0], distance = float(splitNode[1]), heuristic = float(heuristicsNameValues[splitNode[0]]))
                    nodeValues.append(newNode)


                stateSpace[keyNode] = nodeValues
            
            initialState: Node = Node(name = strippedLines[0], distance = 0)
            goalStateNames: list[str] = strippedLines[1].split()

    # no heuristics file
    else:
        with open(stateSpaceFile) as f:
            lines = f.readlines()

            strippedLines: list[str] = list()

            for line in lines:
                if line.startswith("#"):
                    continue
                else:
                    line = line.strip()
                    line = line.rstrip('\n')
                    strippedLines.append(line)

            for line in strippedLines[2:]:
                splitLines = line.split()

                keyNode = splitLines[0].rstrip(':')
                nodeValues: list[Node] = list()

                for splitLine in splitLines[1:]:
                    splitNode = splitLine.split(',')
                    newNode = Node(name = splitNode[0], distance = float(splitNode[1]))
                    nodeValues.append(newNode)


                stateSpace[keyNode] = nodeValues
            
            initialState: Node = Node(name = strippedLines[0], distance = 0)
            goalStateNames: list[str] = strippedLines[1].split()
        
                    

    return stateSpace, initialState, goalStateNames, heuristicsFile

def getPath(initialState: Node, currentState: Node, path: list[Node]) -> list[Node]:
    if (currentState.name == initialState.name):
        path.append(currentState)
        return path
    else:
        path.append(currentState)
        return getPath(initialState = initialState, currentState = currentState.parent, path = path)

def bfs(stateSpace: dict[str, list[Node]], initialState: Node, goalStateNames: list[str]):
    foundSolution: Node = None
    traversedStates: list[Node] = []
    
    openNodes: list[Node] = [initialState]

    while len(openNodes) > 0:
        node = openNodes.pop(0)
        
        if node not in traversedStates:
            traversedStates.append(node)

        if node.name in goalStateNames:
            foundSolution = node
            break

        succNodes = stateSpace[node.name]

        for succNode in succNodes:
            updatedNode = Node(name = succNode.name, distance = node.distance + succNode.distance, parent = node)
            openNodes.append(updatedNode)    
    
    
    print("# BFS")
    if foundSolution:
        path = getPath(initialState = initialState, currentState = foundSolution, path = [])
        path.reverse()
        print("[FOUND_SOLUTION]: yes")
        print(f"[STATES_VISITED]: {len(traversedStates)}")
        print(f"[PATH_LENGTH]: {len(path)}")
        print(f"[TOTAL_COST]: {foundSolution.distance}")
        
        print(f"[PATH]: ", end="")
        for i in range(0, len(path)):
            print(path[i].name, end="")
            
            if not i == len(path) - 1:
                print(" => ", end="")

    else:
        print("[FOUND_SOLUTION]: no")

def ucs(stateSpace: dict[str, list[Node]], initialState: Node, goalStateNames: list[str]):
    foundSolution: Node = None
    traversedStates: list[Node] = []
    
    openNodes: list[Node] = [initialState]

    while len(openNodes) > 0:
        node = openNodes.pop(0)
        
        if node.name not in [n.name for n in traversedStates]:
            traversedStates.append(node)

        if node.name in goalStateNames:
            foundSolution = node
            break

        succNodes = stateSpace[node.name]


        for succNode in succNodes:
            updatedNode = Node(name = succNode.name, distance = node.distance + succNode.distance, parent = node)
            openNodes.append(updatedNode)
        
        openNodes.sort(key = lambda n: n.distance) # the only difference between bfs and ucs, sort by total cumulative cost
    
    
    print("# UCS")
    if foundSolution:
        path = getPath(initialState = initialState, currentState = foundSolution, path = [])
        path.reverse()
        print("[FOUND_SOLUTION]: yes")
        print(f"[STATES_VISITED]: {len(traversedStates)}")
        print(f"[PATH_LENGTH]: {len(path)}")
        print(f"[TOTAL_COST]: {foundSolution.distance}")
        
        print(f"[PATH]: ", end="")
        for i in range(0, len(path)):
            print(path[i].name, end="")
            
            if not i == len(path) - 1:
                print(" => ", end="")

    else:
        print("[FOUND_SOLUTION]: no")

def astar(stateSpace: dict[str, list[Node]], initialState: Node, goalStateNames: list[str], heuristicsFile: str):
    foundSolution: Node = None
    traversedStates: list[Node] = []
    
    openNodes: list[Node] = [initialState]

    while len(openNodes) > 0:
        node = openNodes.pop(0)
        
        if node.name not in [n.name for n in traversedStates]:
            traversedStates.append(node)

        if node.name in goalStateNames:
            foundSolution = node
            break

        succNodes = stateSpace[node.name]


        for succNode in succNodes:
            updatedNode = Node(name = succNode.name, distance = node.distance + succNode.distance, parent = node, heuristic = succNode.heuristic)

            # if there exists a node n in traversedStates or openNodes which has the same name as updatedNode, if not then False
            existing = next((n for n in traversedStates + openNodes if n.name == updatedNode.name), False)

            if existing:
                if existing.distance < updatedNode.distance:
                    continue
                else:
                    if existing in traversedStates:
                        traversedStates.remove(existing)
                    if existing in openNodes:
                        openNodes.remove(existing)

            openNodes.append(updatedNode)
            openNodes.sort(key = lambda n: n.distance + n.heuristic) # factoring in the heuristic as well here
        
    
    
    print(f"# A-STAR {os.path.basename(heuristicsFile)}")
    if foundSolution:
        path = getPath(initialState = initialState, currentState = foundSolution, path = [])
        path.reverse()
        print("[FOUND_SOLUTION]: yes")
        print(f"[STATES_VISITED]: {len(traversedStates)}")
        print(f"[PATH_LENGTH]: {len(path)}")
        print(f"[TOTAL_COST]: {foundSolution.distance}")
        
        print(f"[PATH]: ", end="")
        for i in range(0, len(path)):
            print(path[i].name, end="")
            
            if not i == len(path) - 1:
                print(" => ", end="")

    else:
        print("[FOUND_SOLUTION]: no")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ss', required=True) # path to state space file
    parser.add_argument('--alg', required=True) # search algorithm
    parser.add_argument('--h', default=None) # path to heuristics file
    parser.add_argument('--check-optimistic', default=None) # flag for checking if heuristic is optimistic
    parser.add_argument('--check-consistent', default=None) # flag for checking if herustic is consistent
    args = parser.parse_args()

    stateSpace, initialState, goalStateNames, heuristicsFile =  dataLoading(args.ss, args.h)

    if args.alg == 'bfs':
        bfs(stateSpace, initialState, goalStateNames)
    elif args.alg == 'ucs':
        ucs(stateSpace, initialState, goalStateNames)
    elif args.alg == 'astar':
        astar(stateSpace, initialState, goalStateNames, heuristicsFile)

if __name__ == '__main__':
    main()