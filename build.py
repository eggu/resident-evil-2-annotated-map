"""Build the pinned bilingual snapshot; does not change an installed game."""
from pathlib import Path
import argparse, hashlib, importlib, json, os, shutil, subprocess, sys, zipfile

ROOT = Path(__file__).resolve().parent
EXE_SHA256 = '21b2a647cbeddac1ec389be847f22a434a0264a18020589de91cb2824dcb1bf5'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-exe', type=Path, help='Run native/texture tests with this legally owned executable')
    args = parser.parse_args()
    if args.game_exe:
        args.game_exe = args.game_exe.resolve()
        if hashlib.sha256(args.game_exe.read_bytes()).hexdigest() != EXE_SHA256:
            parser.error('Unsupported executable SHA256; see docs/DEVELOPMENT.md')
    version = (ROOT/'VERSION').read_text().strip()
    build, dist = ROOT/'build', ROOT/'dist'
    build.mkdir(exist_ok=True); dist.mkdir(exist_ok=True)
    for p in (ROOT/'src').iterdir():
        shutil.copy2(p, build/p.name)
    zig_lib = Path(importlib.import_module('ziglang').__file__).parent/'lib'
    subprocess.run([sys.executable,'-m','ziglang','cc','-target','x86-windows-gnu','-shared','-O2',
        '-fno-stack-protector','-DWIN32_LEAN_AND_MEAN','-nostdlib',
        f'-I{zig_lib}/libc/include/any-windows-any','-Wl,--entry,DllMain@12',
        're2_keymap.c','-lkernel32','-luser32','-o','RE2.KeyMapNames-v6.4.asi'],cwd=build,check=True)
    if args.game_exe:
        for p in (ROOT/'tests').glob('*.py'): shutil.copy2(p,build/p.name)
        for p in (ROOT/'data').iterdir(): shutil.copy2(p,build/p.name)
        shutil.copytree(ROOT/'tests/fixtures',build,dirs_exist_ok=True)
        env = dict(os.environ, RE2_GAME_EXE=str(args.game_exe))
        for name in ('test_native-v6.4.py','test_upload-v6.4.py'):
            subprocess.run([sys.executable,name],cwd=build,env=env,check=True,stdout=subprocess.DEVNULL)
    package = dist/f'RE2-Annotated-Map-{version}.zip'
    loader = ROOT/'packaging/ultimate-asi-loader'
    files = {'scripts/RE2.AnnotatedMap.asi': build/'RE2.KeyMapNames-v6.4.asi',
             'scripts/RE2.AnnotatedMap.ini': ROOT/'packaging/RE2.AnnotatedMap.ini',
             'scripts/UltimateASILoader-LICENSE.txt': loader/'UltimateASILoader-LICENSE.txt',
             'dsound.dll': loader/'dsound.dll',
             'RE2-Annotated-Map-README.txt': ROOT/'packaging/README.txt',
             'LICENSE.txt': ROOT/'LICENSE', 'NOTICE.md': ROOT/'NOTICE.md'}
    with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
        for name,source in files.items(): z.write(source,name)
    with zipfile.ZipFile(package) as z:
        assert z.testzip() is None
        assert set(z.namelist()) == set(files)
        for name,source in files.items(): assert z.read(name) == source.read_bytes(), name
    report = dict(version=version,asi_sha256=hashlib.sha256((build/'RE2.KeyMapNames-v6.4.asi').read_bytes()).hexdigest(),
        package_sha256=hashlib.sha256(package.read_bytes()).hexdigest(),native_tests_run=bool(args.game_exe),live_game_tested=False)
    (dist/'build-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2)); print(package)

if __name__ == '__main__': main()
