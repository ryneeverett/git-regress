def pytest_addoption(parser):
    parser.addoption(
        '--write', choices=['std', 'sh', 'all'],
        help="Write 'std' streams, 'sh'ell debug output, or 'all' to console.")
