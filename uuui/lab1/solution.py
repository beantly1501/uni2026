# - python standard library
# https://docs.python.org/3/library/index.html
#
# - how to optimize list lookups
#
# https://datapoints.hashnode.dev/pythondictionarylookups01
# https://stackoverflow.com/questions/2701173/most-efficient-way-for-a-lookup-search-in-a-huge-list-python
#
# - algorithms
# https://en.wikipedia.org/wiki/Breadth-first_search
# https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm#Practical_optimizations_and_infinite_graphs
# https://en.wikipedia.org/wiki/A*_search_algorithm
#
# - consistent and optimal heuristics
# https://www.youtube.com/watch?v=Dqy-43JHte8


import sys

class Transition:
    def __init__(self, startingNodeName, endNodeName, transitionCost):
        self.startingNodeName = startingNodeName
        self.endNodeName = endNodeName
        self.transitionCost = transitionCost

    def getStartingNodeName(self):
        return self.startingNodeName

    def getEndNodeName(self):
        return self.endNodeName

    def getTransitionCost(self):
        return self.transitionCost

    def updateTransitionCost(self, transitionCost):
        self.transitionCost = transitionCost

    def printTransition(self):
        print(f"{self.startingNodeName} -> {self.endNodeName} ({self.transitionCost})")
class Node:
    def __init__(self, name, initialState=False, goalState=False, transitionsList=None, cost=0, heuristic=0, estimatedCost=0):
        self.name = name
        self.transitionsList = transitionsList if transitionsList is not None else []
        self.initialState = initialState
        self.goalState = goalState
        self.heuristic = heuristic
        self.cost = cost
        self.estimatedCost = estimatedCost

    def getName(self):
        return self.name

    def isInitialState(self):
        return self.initialState

    def isGoalState(self):
        return self.goalState

    def getHeuristic(self):
        return self.heuristic

    def addHeuristic(self, heuristic):
        self.heuristic = heuristic

    def getTransitionsList(self):
        return self.transitionsList

    def addTransition(self, transition):
        self.transitionsList.append(transition)

    def getCost(self):
        return self.cost

    def setCost(self, cost):
        self.cost = cost

    def getEstimatedCost(self):
        return self.estimatedCost

    def setEstimatedCost(self, estimatedCost):
        self.estimatedCost = estimatedCost


    def printNode(self):
        print(f"\n--- {self.name} ({self.heuristic}){' (INITIAL)' if self.initialState else ''}{' (GOAL)' if self.goalState else ''} ---")
        for transition in self.transitionsList:
            transition.printTransition()
        print()

def printAlgorithmResult(algName, foundSolution, statesVisited=None, pathLength=None, totalCost=None, path=None):
    print(f"# {algName}")
    print(f"[FOUND_SOLUTION]: {'yes' if foundSolution else 'no'}")
    if foundSolution:
        print(f"[STATES_VISITED]: {statesVisited}")
        print(f"[PATH_LENGTH]: {pathLength}")
        print(f"[TOTAL_COST]: {totalCost}")
        print("[PATH]: ")
        for i in range(len(path)):
            if i + 1 == len(path):
                print(path[i].getName())
                break

            print(f"{path[i].getName()} => ", end="")
def dataLoading(stateDescriptor, heuristicDescriptor=None):
    nodes = []

    with open(stateDescriptor) as f:
        lines = [line for line in f if not line.startswith("#")]
        lines = [line.strip() for line in lines]

    initialStateName = lines[0] # lines[0] is the initial state
    goalStates = lines[1].split() # lines[1] are the goal states (0 or more)

    for i in range(2, len(lines)):
        # first, get the name of the state from which the transitions can be made
        nodeName, unpolishedTransitionsList = lines[i].split(":", 1) # splits the list at the first occurrence of ":"

        newNode = Node(name = nodeName, initialState = nodeName == initialStateName, goalState = nodeName in goalStates)

        if unpolishedTransitionsList:
            # strip whitespaces and split transitions into a list
            transitionsList = unpolishedTransitionsList.strip().split()

            for t in transitionsList:
                transitionNodeName, cost = t.split(",", 1)

                newNode.addTransition(Transition(nodeName, transitionNodeName, float(cost)))

        nodes.append(newNode)

    # if the heuristic descriptor file exists, then add the heuristic descriptions for each node
    if heuristicDescriptor:
        with open(heuristicDescriptor) as f:
            lines = [line for line in f if not line.startswith("#")]
            lines = [line.strip() for line in lines]

        for line in lines:
            nodeName, unpolishedHeuristicDescriptor = line.split(":", 1)
            heuristicDescriptor = float(unpolishedHeuristicDescriptor.strip())

            for node in nodes:
                if node.getName() == nodeName:
                    node.addHeuristic(heuristicDescriptor)
                    break

    return nodes
def generateSuccessorStates(currentNode, nodes):
    successorStates = []

    # get the list of transitions from the current node
    currentNodeTransitions = currentNode.getTransitionsList()
    successorStateNames = []

    # get the names of the states we can transition to from the current state
    for transition in currentNodeTransitions:
        successorStateNames.append(transition.getEndNodeName())

    # get the nodes corresponding to the successor state names
    for node in nodes:
        for successorStateName in successorStateNames:
            if node.getName() == successorStateName:
                successorStates.append(node)
                break

    # return the sorted list of successor states
    return sorted(successorStates, key=lambda n: (n.getCost(), n.getName()))  # sorted by name
def calculateTransitionCost(startingNode, endingNode):
    for transition in startingNode.getTransitionsList():
        if transition.getEndNodeName() == endingNode.getName():
            return transition.getTransitionCost()

    return None

def BFS(nodes, initialState, goalStates):
    open = [initialState] # queue
    parentState = {initialState: None}
    cost = 0
    visitedStates = 0

    while len(open) > 0:
        currentState = open.pop(0) # take the first state in the queue "open"
        visitedStates += 1

        # if we reached the goal state
        if currentState in goalStates:

            # reconstructing the path by looping through the dictionary all the way to the initial state
            path = []
            while currentState is not None:
                path.append(currentState)
                currentState = parentState[currentState] # current state becomes it's parent

            # then the path needs to be reversed, because it's currently going from goal to initial state!!
            path.reverse()
            for i in range(len(path)):
                # check if this is the penultimate element
                if i + 1 == len(path):
                    break

                cost += calculateTransitionCost(path[i], path[i + 1])

            printAlgorithmResult("BFS", True, visitedStates, len(path), cost, path)
            return 0

        # if not, generate the successor states for the current state and add them to the end of the "open" queue
        for successor in generateSuccessorStates(currentState, nodes):
            # if the successor has not been passed, add the current state as it's parent and append to open
            if successor not in parentState:
                parentState[successor] = currentState

                if successor not in open:
                    open.append(successor)

    printAlgorithmResult("BFS", False)
    return 1
def UCS(nodes, initialState, goalStates):
    open = [initialState] # a priority queue, sorted by the cost of reaching a state
    parentState = {initialState: None}
    cost = 0
    visitedStates = 0

    while len(open) > 0:
        currentState = open.pop(0)  # take the first state in the priority queue "open"
        visitedStates += 1

        # if we reached the goal state
        if currentState in goalStates:

            # reconstructing the path by looping through the dictionary all the way to the initial state
            path = []
            while currentState is not None:
                path.append(currentState)
                currentState = parentState[currentState] # current state becomes it's parent

            # then the path needs to be reversed, because it's currently going from goal to initial state!!
            path.reverse()
            for i in range(len(path)):
                # check if this is the penultimate element
                if i + 1 == len(path):
                    break

                cost += calculateTransitionCost(path[i], path[i + 1])

            printAlgorithmResult("UCS", True, visitedStates, len(path), cost, path)
            return 0

        # if not, generate the successor states for the current state and add them to the end of the "open" queue
        for successor in generateSuccessorStates(currentState, nodes):

            # computing the auxiliary cost which will be used for comparison with the successor
            auxCost = currentState.getCost() + calculateTransitionCost(currentState, successor)

            # if the successor has not been passed or if the currentState's cost is smaller than the successor's
            if successor not in parentState or auxCost < successor.getCost():
                parentState[successor] = currentState
                successor.setCost(auxCost) # update the new, smaller cost
                open.append(successor)

                if successor not in open:
                    open.append(successor)

        # sort open by the cost of the state
        open = sorted(open, key=lambda n: n.getCost())

    printAlgorithmResult("UCS", False)
    return 1
def A_STAR(nodes, initialState, goalStates):
    open = [initialState]
    parentState = {initialState: None}
    closed = []
    pathCost = 0
    visitedStateCount = 0

    while len(open) > 0:
        currentState = open.pop(0)  # take the first state in the priority queue "open"
        closed.append(currentState)
        visitedStateCount += 1

        if currentState in goalStates:
            # reconstructing the path
            path = []
            while currentState is not None:
                path.append(currentState)
                currentState = parentState[currentState]

            path.reverse()

            for i in range(len(path)):
                # check if this is the penultimate element
                if i + 1 == len(path):
                    break

                pathCost += calculateTransitionCost(path[i], path[i + 1])

            printAlgorithmResult("A_STAR", True, visitedStateCount, len(path), pathCost, path)
            return 0

        for successor in generateSuccessorStates(currentState, nodes):
            # the additional check of not in closed
            if successor not in closed:

                # again, calculating the auxiliary cost for later comparison with successor
                auxCost = currentState.getCost() + calculateTransitionCost(currentState, successor)

                if successor not in open:
                    open.append(successor)
                elif auxCost >= successor.getCost():
                    continue

                parentState[successor] = currentState
                successor.setCost(auxCost)
                successor.setEstimatedCost(auxCost + successor.getHeuristic())

        open = sorted(open, key=lambda n: n.getEstimatedCost())

# basically UCS, but with no path reconstruction, only returns the true cost of a path
def calculateTrueCost(initialState, nodes, goalStates):
    for node in nodes:
        node.setCost(float('inf')) # using infinite as the largest possible cost

    initialState.setCost(0)
    open = [initialState]

    while len(open) > 0:
        currentState = open.pop(0)

        if currentState in goalStates:
            return currentState.getCost()

        for successor in generateSuccessorStates(currentState, nodes):
            auxCost = currentState.getCost() + calculateTransitionCost(currentState, successor)

            if auxCost < successor.getCost():
                successor.setCost(auxCost)

                if successor not in open:
                    open.append(successor)

        open = sorted(open, key=lambda n: n.getCost())

    return float('inf')

# if a node's heuristic is SMALLER than the true cost of the optimal path
# the heuristic is optimistic
def calculateIfOptimistic(nodes, heuristicDescriptorFile, goalStates):
    print(f"# HEURISTIC-OPTIMISTIC {heuristicDescriptorFile}")

    isOptimistic = True
    sortedNodes = sorted(nodes, key=lambda n: n.getName())

    for node in sortedNodes:
        trueCost = calculateTrueCost(node, nodes, goalStates) # calculate the true cost for a node
        heuristic = node.getHeuristic()

        # for that node, if the heuristic is bigger than the true cost, meaning it OVERestimates
        if heuristic > trueCost:
            print(f"[CONDITION]: [ERR] h({node.getName()}) <= h*: {heuristic:.1f} <= {trueCost:.1f}")
            isOptimistic = False
        else:
            print(f"[CONDITION]: [OK] h({node.getName()}) <= h*: {heuristic:.1f} <= {trueCost:.1f}")

    if isOptimistic:
        print("[CONCLUSION]: Heuristic is optimistic.")
    else:
        print("[CONCLUSION]: Heuristic is not optimistic.")
# if a node's heuristic is SMALLER than the sum of the successor's heuristic and the transition cost,
# the heuristic is consistent
def calculateIfConsistent(nodes, heuristicDescriptorFile):
    print(f"# HEURISTIC-CONSISTENT {heuristicDescriptorFile}")

    isConsistent = True
    sortedNodes = sorted(nodes, key=lambda n: n.getName())

    for node in sortedNodes:
        for transition in node.getTransitionsList():
            for successor in nodes:
                if successor.getName() == transition.getEndNodeName():
                    nodeHeuristic = node.getHeuristic()
                    successorHeuristic = successor.getHeuristic()
                    transitionCost = transition.getTransitionCost()

                    # if a node's heuristic is
                    if nodeHeuristic > successorHeuristic + transitionCost:
                        print(f"[CONDITION]: [ERR] h({node.getName()}) <= h({successor.getName()}) + c: {nodeHeuristic:.1f} <= {successorHeuristic:.1f} + {transitionCost:.1f}")
                        isConsistent = False
                    else:
                        print(f"[CONDITION]: [OK] h({node.getName()}) <= h({successor.getName()}) + c: {nodeHeuristic:.1f} <= {successorHeuristic:.1f} + {transitionCost:.1f}")

    if isConsistent:
        print("[CONCLUSION]: Heuristic is consistent.")
    else:
        print("[CONCLUSION]: Heuristic is not consistent.")

def main():

    args = sys.argv
    stateDescriptor = args[2]
    algorithmName = ''
    heuristicDescriptor = ''
    heuristicsCheck = ''

    if args[3] == '--h':
        heuristicDescriptor = args[4]
        if args[5] == '--check-consistent':
            heuristicsCheck = 'consistent'
        elif args[5] == '--check-optimistic':
            heuristicsCheck = 'optimistic'
    elif args[3] == '--alg':
        algorithmName = args[4]
        heuristicDescriptor = args[6] if len(args) > 5 else None

    nodes = dataLoading(stateDescriptor, heuristicDescriptor)

    # get the initial state
    initialState = None
    goalStates = []

    for node in nodes:
        if node.isInitialState():
            initialState = node

        if node.isGoalState():
            goalStates.append(node)

    if algorithmName == "bfs":
        BFS(nodes, initialState, goalStates)
    elif algorithmName == "ucs":
        UCS(nodes, initialState, goalStates)
    elif algorithmName == "astar":
        A_STAR(nodes, initialState, goalStates)
    elif heuristicsCheck == "consistent":
        calculateIfConsistent(nodes, heuristicDescriptor)
    elif heuristicsCheck == "optimistic":
        calculateIfOptimistic(nodes, heuristicDescriptor, goalStates)

if __name__ == '__main__':
    main()