#!/bin/bash

# 使用 find 命令查找并删除多个目录：__pycache__、build 和 dist
find . -type d \( -name "__pycache__" -o -name ".pytest_cache" \) -exec rm -r {} +

echo "The specified directories (__pycache__, .pytest_cache) have been deleted."
