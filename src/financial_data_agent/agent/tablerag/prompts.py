DECOMPOSE_PROMPT = """\
You will complete a question answering task about the SEC filings of S&P 500 companies. Analyze the Question \
and decide whether it should be broken down into subqueries. After you have collected sufficient information, \
generate a comprehensive answer.

Each subquery is solved for you: passages are retrieved from the filings, and the SQL you write is run against \
the database described below.

Instructions:
1. Carefully analyze the question through step-by-step reasoning.
2. If the question requires multiple pieces of information:
- Decompose the question into subqueries
- Process one subquery at a time
3. If the question can be answered with a single lookup, do not decompose it. Put the original question in \
"subquery".
4. Generate exactly ONE subquery at a time.
5. Write out all terms completely - avoid using abbreviations.
6. When you have sufficient information, provide the final answer.

Reply with exactly one JSON object, in one of these two shapes:
{{"action": "subquery", "subquery": "...", "tickers": ["AAPL"], "years": [2024], "quarters": [3], "sql": "SELECT ..."}}
{{"action": "answer", "answer": "your complete response"}}

"tickers", "years" and "quarters" name the filings the subquery concerns; use [] for any that is not limited. \
"sql" is one PostgreSQL SELECT statement on one line that answers the subquery from the schema below, or null \
when the schema cannot answer it.

Schema:
{schema}

Subqueries solved so far:
{history}
{limit_note}
Question: {question}
Please start!"""

LIMIT_NOTE = "\nYou have used every subquery available. Reply with the answer action now, using the answers above.\n"

INTERMEDIATE_ANSWER_PROMPT = """\
You are about to complete a question answering task about SEC filings using the following two types of reference \
materials:

# Content 1: Original content from the filings (table content is provided in Markdown format)
{docs}

# Content 2: NL2SQL related information and SQL execution results in the database
# the database schema
{schema}

# SQL generated based on the schema and the user question:
{sql}

# SQL execution results
{sql_result}

Please answer the user's question based on the materials above.
User question: {query}

Note:
1. The markdown table content in Content 1 may be not complete.
2. You should cross-validate the given two materials:
- If the answers are the same, you may directly output the answer.
- If the SQL shows an error in "SQL execution results", or was not run, try to answer solely based on Content 1.
- If the two materials conflict, prefer the SQL execution results, which come from the structured metrics, and \
explain the discrepancy."""
