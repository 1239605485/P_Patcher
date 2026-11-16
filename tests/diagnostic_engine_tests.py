"""Run after building the Java classes; optional argument is a real installer diagnostic ZIP."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
cp = os.pathsep.join(str(root/p) for p in ('build/classes', 'toolchain/json.jar', 'toolchain/android.jar'))
with tempfile.TemporaryDirectory(prefix='patcher-diag-test-') as out:
    subprocess.run(['javac', '-source', '8', '-target', '8', '-encoding', 'UTF-8', '-cp', cp, '-d', out,
        *map(str, [root/'tests/DiagnosticCli.java', root/'src/cn/minidayz/patcher/LogEvidence.java',
                    root/'src/cn/minidayz/patcher/LogBundleType.java', root/'src/cn/minidayz/patcher/Diagnosis.java',
                    root/'src/cn/minidayz/patcher/DiagnosticHandoff.java',root/'src/cn/minidayz/patcher/OutputProvenance.java',
                    root/'src/cn/minidayz/patcher/FilesEx.java'])], check=True)
    subprocess.run(['java', '-cp', out+os.pathsep+cp, 'cn.minidayz.patcher.DiagnosticCli', *sys.argv[1:]], check=True)
