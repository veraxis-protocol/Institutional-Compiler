# Engine Adapter Protocol v0.1

Input: exactly one UTF-8 JSON object on stdin with `entry_point` and `input`.

Output: exactly one UTF-8 JSON object on stdout.

Supported entry points: `adjudicate`, `explain_boundary`.

The adapter is responsible for invoking the implementation under test. It must not read frozen expected outputs from the corpus.



