"""Fast single-pass THEIA E3 (CDM18) parser. Keeps every entity participating in a
considered event. THEIA file paths come from the FileObject record's filename field
(unlike CADETS which uses the event predicateObjectPath)."""
import os as _os
_ROOT = _os.environ.get('ALGSE_ROOT', _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..')))
import sys, os, time, re
RUN = os.environ.get('RUNDIR', _os.path.join(_ROOT, 'results', 'theia_e3'))
RAW = os.environ.get('RAWDIR', _os.path.join(_ROOT, 'data', 'theia'))
GT  = os.environ.get('GTFILE', _os.path.join(_ROOT, 'data', 'groundtruth', 'theia.txt'))
default_files = ['ta1-theia-e3-official-6r.json'] + ['ta1-theia-e3-official-6r.json.%d' % i for i in range(1, 13)]
FILES = os.environ.get('PARSE_FILES', ','.join(default_files)).split(',')
pd = RUN + '/parse_data/'
os.makedirs(pd, exist_ok=True)

eventConsider = {'EVENT_READ','EVENT_RECVMSG','EVENT_WRITE','EVENT_SENDMSG','EVENT_FORK',
  'EVENT_CLONE','EVENT_EXECUTE','EVENT_CONNECT','EVENT_UNLINK','EVENT_RENAME',
  'EVENT_CREATE_OBJECT','EVENT_MODIFY_FILE_ATTRIBUTES','EVENT_LOADLIBRARY','EVENT_OPEN','EVENT_MMAP'}

re_subj  = re.compile(r'cdm18\.Subject":\{"uuid":"(.*?)"')
re_cmd   = re.compile(r'"cmdLine":\{"string":"(.*?)"\}')
re_filen = re.compile(r'cdm18\.FileObject":\{"uuid":"(.*?)"(.*?)"filename":"(.*?)"')
re_file  = re.compile(r'cdm18\.FileObject":\{"uuid":"(.*?)"')
re_netf  = re.compile(r'NetFlowObject":\{"uuid":"(.*?)"(.*?)"localAddress":"(.*?)","localPort":(.*?),"remoteAddress":"(.*?)","remotePort":(.*?),')
re_net   = re.compile(r'cdm18\.NetFlowObject":\{"uuid":"(.*?)"')
re_esub  = re.compile(r'"subject":\{"com.bbn.tc.schema.avro.cdm18.UUID":"(.*?)"\}')
re_eobj  = re.compile(r'"predicateObject":\{"com.bbn.tc.schema.avro.cdm18.UUID":"(.*?)"\}')
re_etype = re.compile(r'"type":"(.*?)"')
re_etime = re.compile(r'"timestampNanos":(.*?),')

subj, files, nets = {}, {}, {}
events = []
t0 = time.time()
for fn in FILES:
    path = RAW + fn
    if not os.path.exists(path):
        print('MISSING', fn, flush=True); continue
    with open(path, encoding='utf-8', errors='ignore') as f:
        for line in f:
            if 'cdm18.Event"' in line:
                if 'EVENT_FLOWS_TO' in line:
                    continue
                su = re_esub.search(line); ou = re_eobj.search(line); ty = re_etype.search(line)
                if not (su and ou and ty):
                    continue
                t = ty.group(1)
                if t not in eventConsider:
                    continue
                tm = re_etime.search(line)
                events.append((su.group(1), t, ou.group(1), tm.group(1) if tm else '0'))
            elif 'cdm18.Subject"' in line:
                m = re_subj.search(line)
                if m:
                    c = re_cmd.search(line)
                    subj[m.group(1)] = c.group(1) if c else 'null'
            elif 'cdm18.FileObject"' in line:
                m = re_filen.search(line)
                if m:
                    files[m.group(1)] = m.group(3)
                else:
                    m2 = re_file.search(line)
                    if m2 and m2.group(1) not in files:
                        files[m2.group(1)] = ''
            elif 'cdm18.NetFlowObject"' in line:
                m = re_netf.search(line)
                if m:
                    nets[m.group(1)] = m.group(3)+','+m.group(4)+','+m.group(5)+','+m.group(6)
                else:
                    m2 = re_net.search(line)
                    if m2 and m2.group(1) not in nets:
                        nets[m2.group(1)] = 'null'

used = set()
for su, t, ou, tm in events:
    used.add(su); used.add(ou)
entity_id = {}
nid = 0
sub_rows, file_rows, net_rows, other_rows = [], [], [], []
for u in subj:
    if u in used:
        entity_id[u] = nid; sub_rows.append(str(nid)+': '+subj[u]); nid += 1
for u in files:
    if u in used and u not in entity_id:
        entity_id[u] = nid; file_rows.append(str(nid)+': '+files[u]); nid += 1
for u in nets:
    if u in used and u not in entity_id:
        entity_id[u] = nid; net_rows.append(str(nid)+': '+nets[u]); nid += 1
for u in used:
    if u not in entity_id:
        entity_id[u] = nid; other_rows.append(str(nid)+': other'); nid += 1

def w(name, rows):
    with open(pd+name, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(rows))
w('subject.txt', sub_rows); w('file.txt', file_rows); w('socket.txt', net_rows); w('other.txt', other_rows)
w('event.txt', [str(entity_id[su])+' '+t+' '+str(entity_id[ou])+' '+tm for su, t, ou, tm in events])
w('id_to_uuid.txt', [str(entity_id[u])+' '+u for u in entity_id])
gt = [l.strip() for l in open(GT) if l.strip()]
gtrows = [str(entity_id[u])+' '+u for u in gt if u in entity_id]
w('groundtruth_nodeId.txt', gtrows)
print('THEIA_PARSE_DONE entities', nid, 'events', len(events), 'subjects', len(sub_rows),
      'files', len(file_rows), 'nets', len(net_rows), 'other', len(other_rows),
      'gt_total', len(gt), 'gt_matched', len(gtrows), 'sec', round(time.time()-t0, 1), flush=True)
