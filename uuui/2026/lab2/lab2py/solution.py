from __future__ import annotations
import argparse
from itertools import combinations

def parseResolution(file) -> tuple[set[frozenset[str]], frozenset[str]]:
    with open(file, 'r') as f:
        data = f.read()
        clauses = []
        goalClause = frozenset()

        for line in data.splitlines():
            clause = set()
            line = line.strip().lower()

            if not line:
                continue

            literals = line.split(" v ")
            for lit in literals:
                lit = lit.strip()
                clause.add(lit)
            clauses.append(frozenset(clause))

    goalClause = clauses.pop()
    return set(clauses), goalClause

def resolve(clause1: frozenset[str], clause2: frozenset[str]) -> set[frozenset[str]]:
    resolvents = set()
    for lit1 in clause1:
        for lit2 in clause2:
            if lit1 == f"~{lit2}" or f"~{lit1}" == lit2:
                # remove the literals being resolved and combine the rest
                newClause = (clause1 - {lit1}) | (clause2 - {lit2})
                resolvents.add(newClause)
    return resolvents

def negate(clause: frozenset[str]) -> set[frozenset[str]]:
    negated = set()
    for lit in clause:
        if "~" not in lit:
            neg = f"~{lit}"
        else:
            neg = lit[1:]

        negated.add(frozenset({neg}))
    return negated

def isTautology(clause: frozenset[str]) -> bool:
    for lit in clause:
        if "~" not in lit:
            neg = f"~{lit}"
        else:
            neg = lit[1:]

        if neg in clause:
            return True
    return False

def isSubsumed(possiblySubsumed: frozenset[str], clauses: set[frozenset[str]]) -> bool:
    return any(existing <= possiblySubsumed for existing in clauses)

def removeSubsumed(newClause: frozenset[str], clausesList: set[frozenset[str]]) -> set[frozenset[str]]:
    return {clause for clause in clausesList if not newClause <= clause}

def getAncestors(clause: frozenset[str], childParents: dict[frozenset[str], tuple]) -> set[frozenset[str]]:
    ancestors = set()
    open = [clause]
    while open:
        c = open.pop()
        if c in ancestors:
            continue
        ancestors.add(c)
        parent1, parent2 = childParents.get(c, (None, None))
        if parent1 is not None:
            open.append(parent1)
            open.append(parent2)
    return ancestors

def printResolutionSteps(allClauses: dict[frozenset[str], int], childParents: dict[frozenset[str], tuple[frozenset[str] | None, frozenset[str] | None]], premisesEnd: int):
    ancestors = getAncestors(frozenset(), childParents)

    # keep only clauses needed for constructing the proof in their original order
    proofClauses = [c for c, _ in allClauses.items() if c in ancestors]

    # assign new consecutive indices, after cherrypicking ancestors from allClauses
    reindex = {c: i for i, c in enumerate(proofClauses, 1)}

    # number of premises that are ancestors
    lastPremise = len([c for c in proofClauses if allClauses[c] <= premisesEnd])

    for clause in proofClauses:
        i = reindex[clause]
        parent1, parent2 = childParents[clause]
        clauseStr = "NIL" if not clause else " v ".join(clause)
        if parent1 is None:
            print(f"{i}. {clauseStr}")
        else:
            print(f"{i}. {clauseStr} ({reindex[parent1]}, {reindex[parent2]})")
        if i == lastPremise:
            print("===============")
    print("===============")

def refutationResolution(clauses: set[frozenset[str]], goalClause: frozenset[str]):
    allClauses: dict[frozenset[str], int] = {clause: i for i, clause in enumerate(clauses, 1)}
    childParents: dict[frozenset[str], tuple[frozenset[str] | None, frozenset[str] | None]] = {clause: (None, None) for clause in clauses}

    # negate the goal and add it to the clauses
    negated = negate(goalClause)
    clauses |= set(negated)
    for clause in negated:
        allClauses[clause] = len(allClauses) + 1
        childParents[clause] = (None, None)

    premisesEnd = len(allClauses)

    # remove tautologies from initial clauses
    clauses = {clause for clause in clauses if not isTautology(clause)}

    # set of support
    sos = set(negated)

    while True:
        pairs = [
            (ci, cj)
            for ci, cj in combinations(clauses, 2)
            if ci in sos or cj in sos  # only consider pairs where at least one clause is in the set of support
        ]
        new = set()
        # child parent relationships for new resolvents
        newParents: dict[frozenset[str], tuple[frozenset[str], frozenset[str]]] = {}

        for (ci, cj) in pairs:
            resolvents = resolve(ci, cj)

            if frozenset() in resolvents:
                nil = frozenset()
                allClauses[nil] = len(allClauses) + 1
                childParents[nil] = (ci, cj)
                printResolutionSteps(allClauses, childParents, premisesEnd)
                goalStr = " v ".join(goalClause)
                print(f"[CONCLUSION]: {goalStr} is true")
                return

            for r in resolvents:
                if isTautology(r):
                    continue
                if not isSubsumed(r, clauses) and r not in newParents:
                    new.add(r)
                    newParents[r] = (ci, cj)

        # remove from new anything subsumed by a stronger element in new
        new = {r for r in new if not any(stronger < r for stronger in new)}

        for resolvent in new:
            if resolvent not in allClauses:
                allClauses[resolvent] = len(allClauses) + 1
                childParents[resolvent] = newParents[resolvent]

        # remove from clauses anything subsumed by a new resolvent
        for resolvent in new:
            clauses = removeSubsumed(resolvent, clauses)

        sos.update(new)

        # if new is subset of clauses, then stop
        if new <= clauses:
            goalStr = " v ".join(goalClause)
            print(f"[CONCLUSION]: {goalStr} is unknown")
            return

        # clauses <- clauses U new
        clauses |= new

def cooking(sampleFile, inputFile):
    clauses = set()
    orderedClauses = []

    with open(sampleFile, 'r') as f:
        for line in f:
            line = line.strip().lower()
            if not line:
                continue
            clause = frozenset(lit.strip() for lit in line.split(" v "))
            if clause not in clauses:
                clauses.add(clause)
                orderedClauses.append(clause)

    print("Constructed with knowledge:")
    for clause in orderedClauses:
        print(" v ".join(clause))

    with open(inputFile, 'r') as f:
        for line in f:
            line = line.strip().lower()
            if not line:
                continue
            clauseStr, cmd = line.rsplit(' ', 1)
            clauseStr = clauseStr.strip()
            clause = frozenset(lit.strip() for lit in clauseStr.split(" v "))

            print(f"User's command: {clauseStr} {cmd}")

            if cmd == '?':
                refutationResolution(clauses.copy(), clause)
            elif cmd == '+':
                clauses.add(clause)
                print(f"Added {clauseStr}")
            elif cmd == '-':
                clauses.discard(clause)
                print(f"removed {clauseStr}")

def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='mode', required=True)

    resolution_parser = subparsers.add_parser('resolution')
    resolution_parser.add_argument('resolution_sample')

    cooking_parser = subparsers.add_parser('cooking')
    cooking_parser.add_argument('cooking_sample')
    cooking_parser.add_argument('cooking_input')

    args = parser.parse_args()

    if args.mode == 'resolution':
        clauses, goalClause = parseResolution(args.resolution_sample)
        refutationResolution(clauses, goalClause)

    elif args.mode == 'cooking':
        cooking(args.cooking_sample, args.cooking_input)

if __name__ == '__main__':
    main()
