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
    heuristicsNameValues: dict[str, float] = dict()

    # with heuristics file
    if heuristicsFile:

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
        
                    

    return stateSpace, initialState, goalStateNames, heuristicsFile, heuristicsNameValues

def getPath(initialState: Node, currentState: Node, path: list[Node]) -> list[Node]:
    if (currentState.name == initialState.name):
        path.append(currentState)
        return path
    else:
        path.append(currentState)
        return getPath(initialState = initialState, currentState = currentState.parent, path = path)

def calculateTrueCost(initialNode: Node, stateSpace: dict[str, list[Node]], goalStateNames: list[str]):
    openNodes: list[Node] = [Node(name=initialNode.name, distance=0.0)]

    traversedStates: list[Node] = []

    while len(openNodes) > 0:
        currentState = openNodes.pop(0)

        # because if the node appears again, it has to be because it has the equal 
        # or worse cost (because we sort openNodes by distance), so no point in appending the node to openNodes
        if currentState.name in [n.name for n in traversedStates]:
            continue

        traversedStates.append(currentState)

        if currentState.name in goalStateNames:
            return currentState.distance

        for successor in sorted(stateSpace[currentState.name], key=lambda n: n.name): # sorted because output needs to be alphabetical
            if successor.name not in [n.name for n in traversedStates]:
                openNodes.append(Node(name=successor.name, distance=currentState.distance + successor.distance))

        openNodes.sort(key=lambda n: n.distance)

    return float('inf')

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

            # if there exists a node n in traversedStates or openNodes 
            # which has the same name as updatedNode, if not then False
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
        print("") # prints newline

    else:
        print("[FOUND_SOLUTION]: no")

# if a node's heuristic is smaller or equal to the successor's distance + successor's heuristic for every node, then consistent
def checkConsistent(stateSpace: dict[str, list[Node]], heuristics: dict[str, float], heuristicsFile):
    consistent = True

    print(f"# HEURISTIC-CONSISTENT {os.path.basename(heuristicsFile)}")

    for nodeName, successors in stateSpace.items():
        nodeHeuristic = float(heuristics[nodeName])

        for succ in successors:
            successorHeuristic = float(heuristics[succ.name])

            if nodeHeuristic > succ.distance + successorHeuristic:
                consistent = False
                print(f"[CONDITION]: [ERR] h({nodeName}) <= h({succ.name}) + c: {nodeHeuristic} <= {successorHeuristic} + {succ.distance}")
            else:
                print(f"[CONDITION]: [OK] h({nodeName}) <= h({succ.name}) + c: {nodeHeuristic} <= {successorHeuristic} + {succ.distance}")

    if consistent:
        print("[CONCLUSION]: Heuristic is consistent.")
    else:
        print("[CONCLUSION]: Heuristic is not consistent.")

# if a node's heuristic is smaller or equal to the true cost of the optimal path, then optimistic
def checkOptimistic(stateSpace: dict[str, list[Node]], heuristics: dict[str, float], goalStateNames: list[str], heuristicsFile: str):
    optimistic = True

    print(f"# HEURISTIC-OPTIMISTIC {os.path.basename(heuristicsFile)}")

    for nodeName in sorted(stateSpace.keys()): # sorted because the output needs to display alphabetically
        nodeHeuristic = float(heuristics.get(nodeName, 0.0))
        trueCost = calculateTrueCost(Node(name=nodeName, distance=0.0), stateSpace, goalStateNames)

        if nodeHeuristic > trueCost:
            optimistic = False
            print(f"[CONDITION]: [ERR] h({nodeName}) <= h*: {nodeHeuristic} <= {trueCost}")
        else:
            print(f"[CONDITION]: [OK] h({nodeName}) <= h*: {nodeHeuristic} <= {trueCost}")

    if optimistic:
        print("[CONCLUSION]: Heuristic is optimistic.")
    else:
        print("[CONCLUSION]: Heuristic is not optimistic.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ss', required=True) # path to state space file
    parser.add_argument('--alg', default=None) # search algorithm
    parser.add_argument('--h', default=None) # path to heuristics file
    parser.add_argument('--check-optimistic', action='store_true') # flag for checking if heuristic is optimistic
    parser.add_argument('--check-consistent', action='store_true') # flag for checking if herustic is consistent
    args = parser.parse_args()

    stateSpace, initialState, goalStateNames, heuristicsFile, heuristicsNameValues =  dataLoading(args.ss, args.h)

    if args.alg == 'bfs':
        bfs(stateSpace, initialState, goalStateNames)
    elif args.alg == 'ucs':
        ucs(stateSpace, initialState, goalStateNames)
    elif args.alg == 'astar':
        astar(stateSpace, initialState, goalStateNames, heuristicsFile)
    
    if args.check_consistent:
        checkConsistent(stateSpace, heuristicsNameValues, heuristicsFile)

    if args.check_optimistic:
        checkOptimistic(stateSpace, heuristicsNameValues, goalStateNames, heuristicsFile)
    

if __name__ == '__main__':
    main()