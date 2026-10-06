import ast
import logging
import math
import operator
import re

from .formatting_service import format_number_es

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
    "sen": math.sin,
    "sin": math.sin,
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
        raise ValueError(f"Constante no permitida: {node.value}")

    def visit_Num(self, node):
        return node.n

    def visit_BinOp(self, node):
        op_type = type(node.op)
        if op_type not in _ALLOWED_BIN_OPS:
            raise ValueError(f"Operador no permitido: {type(node.op).__name__}")
        left = self.visit(node.left)
        right = self.visit(node.right)
        if op_type is ast.Div and right == 0:
            raise ZeroDivisionError
        return _ALLOWED_BIN_OPS[op_type](left, right)

    def visit_UnaryOp(self, node):
        op_type = type(node.op)
        if op_type not in _ALLOWED_UNARY_OPS:
            raise ValueError(f"Operador unario no permitido: {type(node.op).__name__}")
        operand = self.visit(node.operand)
        return _ALLOWED_UNARY_OPS[op_type](operand)

    def visit_Call(self, node):
        if not isinstance(node.func, ast.Name):
            raise ValueError(f"Función inválida: {ast.dump(node.func)}")
        func_name = node.func.id.lower()
        if func_name not in _ALLOWED_FUNCS:
            raise ValueError(f"Función no permitida: {func_name}")
        args = [self.visit(arg) for arg in node.args]
        return _ALLOWED_FUNCS[func_name](*args)

    def visit_Name(self, node):
        name_lower = node.id.lower()
        if name_lower in _ALLOWED_CONSTS:
            return _ALLOWED_CONSTS[name_lower]
        raise ValueError(f"Nombre no permitido: {node.id}")

    def generic_visit(self, node):
        raise ValueError(f"Expresión no permitida: {type(node).__name__}")


def normalizar_expresion(expr: str) -> str:
    expr = (expr or "").strip().lower()

    # Paso 1: Reemplazar frases completas en orden correcto (más largos primero!
    reemplazos = [
        ("raíz cuadrada de", "sqrt"),
        ("raiz cuadrada de", "sqrt"),
        ("raíz de", "sqrt"),
        ("raiz de", "sqrt"),
        ("al cuadrado", "**2"),
        ("al cubo", "**3"),
        ("elevado a", "**"),
        ("multiplicado por", "*"),
        ("dividido por", "/"),
        ("más", "+"),
        ("mas", "+"),
        ("menos", "-"),
        ("por", "*"),
        ("entre", "/"),
        ("x", "*"),
        ("×", "*"),
        ("÷", "/"),
        ("^", "**"),
        (",", "."),
    ]

    for src, dst in reemplazos:
        expr = expr.replace(src, dst)

    # Paso 2: Manejar "raiz X", "sqrt X", "sen X", etc.
    # Ahora que tenemos "sqrt 4" → transformar a sqrt(4)
    for func_name in _ALLOWED_FUNCS.keys():
        # Patrón para "func X" → func(X) - USAMOS \b para límites de palabra!
        expr = re.sub(
            rf"\b{func_name}\s+([\d\.\(\)\+\-\*\/]+)",
            rf"{func_name}(\1)",
            expr,
            flags=re.IGNORECASE,
        )

    # Paso 3: Manejar números seguidos de paréntesis y viceversa
    expr = re.sub(r"(\d)(\()", r"\1*\2", expr)
    expr = re.sub(r"(\))(\d)", r"\1*\2", expr)

    # Paso 4: Eliminar espacios extra para que el AST lo parse bien
    expr = re.sub(r"\s+", "", expr)
    return expr


def evaluar_expresion_matematica(expr: str):
    expr_original = (expr or "").strip()
    if not expr_original:
        return None

    try:
        expr_final = normalizar_expresion(expr_original)
        logger.info(f"Evaluando: {expr_final}")

        parsed = ast.parse(expr_final, mode="eval")
        resultado = SafeMathEvaluator().visit(parsed)

        if isinstance(resultado, float):
            if resultado.is_integer():
                resultado = int(resultado)
            else:
                resultado = round(resultado, 6)

        return f"El resultado de {expr_original} es {format_number_es(resultado)}."
    except ZeroDivisionError:
        return "No se puede dividir entre cero."
    except Exception:
        logger.exception("Error evaluando expresión matemática")
        return None
