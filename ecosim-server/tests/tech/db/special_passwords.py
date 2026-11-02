SPECIAL_PASSWORDS = [
    "p@ssword",
    "pass/word",
    "pass#word",
    "pass%word",
    "pass%41word",
    "100%",
    "%%",
    "%(server)s",
    "p:a?s&s=w+o rd",
    "a@b/c#d%e",
]
# every part is distinctive, so finding one in a message cannot be a coincidence
PASSWORD_PARTS = ["hunter7", "zebra9", "quartz5", "mango3"]
PASSWORD_WITH_PARTS = "hunter7@zebra9/quartz5#mango3%41"
