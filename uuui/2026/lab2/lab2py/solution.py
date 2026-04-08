from __future__ import annotations
import argparse
import os
from itertools import combinations

def parseResolution(file) -> tuple[set[frozenset[str]], frozenset[str]]:
    with open(file, 'r') as f:
        data = f.read()
        clauses = []
        goalClause = frozenset()

        for line in data.splitlines():
            clause = set()
            line = line.strip()
            line = line.lower()

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

def refutationResolution(clauses: set[frozenset[str]], goalClause: frozenset[str]):
    # negate the goal and add it to the clauses
    negated = negate(goalClause)
    clauses |= set(negated)

    clauses = {clause for clause in clauses if not isTautology(clause)}

    sos = set(negated)

    while True:
        # at least one of ci, cj must be in SOS
        pairs = [
            (ci, cj)
            for ci, cj in combinations(clauses, 2)
            if ci in sos or cj in sos  # only consider pairs where at least one clause is in the set of support
        ]
        new = set()

        for (ci, cj) in pairs:
            # resolving two pairs means finding a pair of complementary literals
            # and creating a new clause that is the union of the two clauses
            # minus the complementary literals
            resolvents = resolve(ci, cj)
            if frozenset() in resolvents:
                goalStr = " v ".join(goalClause)

                print(f"[CONCLUSION]: {goalStr} is true")
                return

            for r in resolvents:
                if isTautology(r):
                    continue
                new.add(r)

        # remove from clauses anything subsumed by a new resolvent
        for r in new:
            clauses = removeSubsumed(r, clauses)

        # remove from new anything strictly subsumed by another element in new
        new = {r for r in new if not any(other < r for other in new)}

        sos.update(new)

        # if new is subset of clauses, then stop
        if new <= clauses:
            goalStr = " v ".join(goalClause)

            print(f"[CONCLUSION]: {goalStr} is unknown")
            return

        # clauses <- clauses U new
        clauses |= new

def parseCooking(sampleFile, inputFile):
    with open(sampleFile, 'r') as f:
        sampleData = f.read()
        print(sampleData)

    with open(inputFile, 'r') as f:
        inputData = f.read()
        print(inputData)

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
        parseCooking(args.cooking_sample, args.cooking_input)

if __name__ == '__main__':
    main()
