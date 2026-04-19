"""SQL statement splitter for migration runner."""


def _is_comment_only(stmt: str) -> bool:
    s = stmt
    while s:
        s = s.lstrip()
        if not s:
            return True
        if s.startswith("--"):
            nl = s.find("\n")
            s = s[nl + 1:] if nl != -1 else ""
        elif s.startswith("/*"):
            end = s.find("*/", 2)
            s = s[end + 2:] if end != -1 else ""
        else:
            return False
    return True


def split_sql_statements(sql: str) -> list[str]:
    """
    Split a SQL script into individual statements.

    Handles dollar-quoted blocks ($$...$$, $tag$...$tag$),
    single-quoted literals with '' escapes, line and block comments.
    """
    statements: list[str] = []
    buf: list[str] = []
    i, n = 0, len(sql)

    while i < n:
        ch = sql[i]

        if ch == "-" and i + 1 < n and sql[i + 1] == "-":
            j = sql.find("\n", i)
            j = n if j == -1 else j + 1
            buf.append(sql[i:j]); i = j; continue

        if ch == "/" and i + 1 < n and sql[i + 1] == "*":
            j = sql.find("*/", i + 2)
            j = n if j == -1 else j + 2
            buf.append(sql[i:j]); i = j; continue

        if ch == "$":
            j = sql.find("$", i + 1)
            if j != -1:
                inner = sql[i + 1:j]
                if all(c.isalnum() or c == "_" for c in inner):
                    tag = sql[i:j + 1]
                    end = sql.find(tag, j + 1)
                    if end != -1:
                        buf.append(sql[i:end + len(tag)])
                        i = end + len(tag)
                        continue

        if ch == "'":
            j = i + 1
            while j < n:
                if sql[j] == "'":
                    if j + 1 < n and sql[j + 1] == "'":
                        j += 2
                    else:
                        j += 1; break
                else:
                    j += 1
            buf.append(sql[i:j]); i = j; continue

        if ch == ";":
            buf.append(";")
            stmt = "".join(buf).strip()
            if stmt and stmt != ";":
                statements.append(stmt)
            buf = []; i += 1; continue

        buf.append(ch); i += 1

    remaining = "".join(buf).strip()
    if remaining and not _is_comment_only(remaining):
        statements.append(remaining)

    return statements
