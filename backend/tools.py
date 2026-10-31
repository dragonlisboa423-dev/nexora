"""Ferramentas determinísticas: nenhuma execução de código, rede ou shell."""

import ast
import math
import operator

OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}


def calculate(expression: str):
    if len(expression) > 200:
        raise ValueError("Expressão muito longa")

    def walk(node, depth=0):
        if depth > 15:
            raise ValueError("Expressão muito complexa")
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            value = node.value
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = walk(node.operand, depth + 1) * (-1 if isinstance(node.op, ast.USub) else 1)
        elif isinstance(node, ast.BinOp) and type(node.op) in OPS:
            left, right = walk(node.left, depth + 1), walk(node.right, depth + 1)
            if isinstance(node.op, ast.Pow) and abs(right) > 20:
                raise ValueError("Expoente excede o limite")
            value = OPS[type(node.op)](left, right)
        else:
            raise ValueError("Apenas números e operações aritméticas são permitidos")
        if isinstance(value, complex) or not math.isfinite(value) or abs(value) > 1e100:
            raise ValueError("Resultado fora dos limites")
        return value

    return walk(ast.parse(expression, mode="eval").body)
