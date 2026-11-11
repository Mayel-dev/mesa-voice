"""Run a temporary localhost server and verify the device's raw HTTP contract.
Uses mock mode only. Does not load or contact an AI model. No firewall changes.
"""
import os,sys,subprocess,socket,time,secrets,json,struct,http.client
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from mesa_voice.audio import encode_wav,decode_wav
token=secrets.token_hex(24)
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
env={**os.environ,'MESA_TOKEN':token,'MESA_MODE':'mock'}
log=ROOT/'validation'/'transport-server.log'
with log.open('w') as f:
    p=subprocess.Popen([sys.executable,'-m','uvicorn','mesa_voice.app:create_app','--factory','--host','127.0.0.1','--port',str(port),'--workers','1','--no-access-log'],cwd=ROOT/'backend',env=env,stdout=f,stderr=f)
    try:
        for _ in range(100):
            try:
                c=http.client.HTTPConnection('127.0.0.1',port,timeout=2);c.request('GET','/healthz');r=c.getresponse();health=json.loads(r.read());c.close();break
            except OSError:time.sleep(.1)
        else:raise RuntimeError('Server did not start')
        body=encode_wav(bytes(16000*2//4))
        c=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
        c.request('POST','/v1/voice',body,{'Authorization':'Bearer '+token,'Content-Type':'audio/wav','Connection':'close'})
        r=c.getresponse();reply=r.read();headers=dict(r.getheaders())
        assert r.status==200 and r.getheader('Content-Type')=='audio/wav'
        assert int(r.getheader('Content-Length'))==len(reply)==8044
        assert r.getheader('Transfer-Encoding') is None
        assert r.getheader('X-Mesa-Mode')=='mock';decode_wav(reply)
        c.close()
        (ROOT/'validation'/'mock-reply.wav').write_bytes(reply)
        report={'passed':True,'server':'uvicorn localhost, ephemeral port','mode':'mock','health':health,'status':200,'response_bytes':len(reply),'pcm_rate':16000,'pcm_bits':16,'channels':1,'duration_seconds':.25,'canonical_wav':True,'real_ai_inference_tested':False}
        (ROOT/'validation'/'transport.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(report,indent=2))
    finally:
        p.terminate()
        try:p.wait(timeout=5)
        except subprocess.TimeoutExpired:p.kill();p.wait()
