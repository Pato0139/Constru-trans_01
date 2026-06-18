import ast
import math
import operator
import re
import logging

logger = logging.getLogger(__name__)

_ALLOWED_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}

_ALLOWED_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

_ALLOWED_FUNCS = {
    "sin": math.sin,
    "sen": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "sqrt": math.sqrt,
    "abs": abs,
    "round": round,
    "ln": math.log,
    "log": math.log10,
    "exp": math.exp,
    "fact": math.factorial,
    "factorial": math.factorial,
}

_ALLOWED_CONSTS = {
    "pi": math.pi,
    "e": math.e,
}


class SafeMathEvaluator(ast.NodeVisitor):
    def visit_Expression(self, node):
        return self.visit(node.body)

    def visit_Constant(self, node):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("Constante no permitida")

    def visit_Num(self, node):
        return node.n

    def visit_BinOp(self, node):
        op_type = type(node.op)
        if op_type not in _ALLOWED_BIN_OPS:
            raise ValueError("Operador no permitido")
        left = self.visit(node.left)
        right = self.visit(node.right)
        if op_type is ast.Div and right == 0:
            raise ZeroDivisionError
        return _ALLOWED_BIN_OPS[op_type](left, right)

    def visit_UnaryOp(self, node):
        op_type = type(node.op)
        if op_type not in _ALLOWED_UNARY_OPS:
            raise ValueError("Operador unario no permitido")
        operand = self.visit(node.operand)
        return _ALLOWED_UNARY_OPS[op_type](operand)

    def visit_Call(self, node):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Función inválida")
        func_name = node.func.id
        if func_name not in _ALLOWED_FUNCS:
            raise ValueError("Función no permitida")
        args = [self.visit(arg) for arg in node.args]
        return _ALLOWED_FUNCS[func_name](*args)

    def visit_Name(self, node):
        if node.id in _ALLOWED_CONSTS:
            return _ALLOWED_CONSTS[node.id]
        raise ValueError(f"Nombre no permitido: {node.id}")

    def generic_visit(self, node):
        raise ValueError(f"Expresión no permitida: {type(node).__name__}")


def normalizar_expresion(expr: str) -> str:
    expr = (expr or "").strip().lower()

    reemplazos = [
        ("multiplicado por", "*"),
        ("dividido por", "/"),
        ("raíz cuadrada de", "sqrt"),
        ("raiz cuadrada de", "sqrt"),
        ("al cuadrado", "**2"),
        ("al cubo", "**3"),
        ("más", "+"),
        ("mas", "+"),
        ("menos", "-"),
        ("por", "*"),
        ("entre", "/"),
        ("x", "*"),
        ("^", "**"),
        (",", "."),
    ]

    for src, dst in reemplazos:
        expr = expr.replace(src, dst)

    expr = re.sub(r"ra[íi]z\s+([\d\.]+)", r"sqrt(\1)", expr, flags=re.IGNORECASE)
    expr = re.sub(r"sqrt\s+([\d\.]+)", r"sqrt(\1)", expr, flags=re.IGNORECASE)
    expr = re.sub(r"(\d)(\()", r"\1*\2", expr)
    expr = re.sub(r"(\))(\d)", r"\1*\2", expr)
    expr = re.sub(r"\s+", "", expr)
    return expr


def evaluar_expresion_matematica(expr: str):
    expr_original = (expr or "").strip()
    if not expr_original:
        return None

    try:
        expr_final = normalizar_expresion(expr_original)
        parsed = ast.parse(expr_final, mode="eval")
        resultado = SafeMathEvaluator().visit(parsed)

        if isinstance(resultado, float):
            resultado = int(resultado) if resultado.is_integer() else round(resultado, 6)

        return f"El resultado de {expr_original} es {resultado}."
    except ZeroDivisionError:
        return "No se puede dividir entre cero."
    except Exception:
        logger.exception(f"Error evaluando expresión matemática: {expr_original}")
        return None
