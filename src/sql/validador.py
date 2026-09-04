import sqlglot
from sqlglot import expressions as exp

class ConsultaInsegura(Exception):
    pass

LIMITE_MAXIMO = 100

def validar_sql(sql: str) -> str:
    try:
        statements = sqlglot.parse(sql, dialect="postgres")
    except Exception as e:
        raise ConsultaInsegura(f"SQL no parseable: {e}")

    if len(statements) != 1:
        raise ConsultaInsegura("Solo se permite una sentencia")

    arbol = statements[0]
    if arbol is None or not isinstance(arbol, exp.Select):
        raise ConsultaInsegura("Solo se permiten consultas SELECT")

    prohibidas = (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Alter)
    for nodo in arbol.walk():
        if isinstance(nodo, prohibidas):
            raise ConsultaInsegura(f"Operación no permitida: {type(nodo).__name__}")

    if arbol.args.get("limit") is None:
        arbol = arbol.limit(LIMITE_MAXIMO)

    return arbol.sql(dialect="postgres")