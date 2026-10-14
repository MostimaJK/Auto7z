import time,json,sys,subprocess,statistics
from pathlib import Path
root=Path(__file__).resolve().parents[1]
if '--child' in sys.argv:
    t=time.perf_counter();sys.path.insert(0,str(root))
    from PyQt5.QtWidgets import QApplication
    import main
    if '--eager' in sys.argv:
        def eager(factory,name,parent):return factory(parent)
        main.LazyPage=eager
    app=QApplication([]);window=main.MainWindow();window.show();app.processEvents();window.grab()
    print('RESULT '+json.dumps({'first_frame_seconds':time.perf_counter()-t}));window.hide()
else:
    output={}
    for name,flags in [('eager',['--eager']),('lazy',[])]:
        values=[]
        for _ in range(5):
            p=subprocess.run([sys.executable,__file__,'--child']+flags,capture_output=True,text=True,encoding='utf-8',errors='replace',check=True)
            values.append(json.loads(next(line[7:] for line in p.stdout.splitlines() if line.startswith('RESULT ')))['first_frame_seconds'])
        output[name]={'samples':values,'median_seconds':statistics.median(values)}
    print(json.dumps(output,indent=2));(root/'artifacts'/'startup-benchmark.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
