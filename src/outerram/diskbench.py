from __future__ import annotations

import os
import platform
import random
import secrets
import shutil
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path

try:
    import fcntl
except ImportError:
    fcntl = None

_MIB=1024*1024; _KIB=1024; _MAX_BENCHMARK_SIZE_MIB=2048; _MAX_CHUNK_MIB=64; _MAX_RANDOM_READ_KIB=16*1024; _MAX_RANDOM_READS=4096

@dataclass(frozen=True)
class DiskBenchmark:
    path:str; size_mib:int; write_mib_s:float; read_mib_s:float; random_read_mib_s:float; random_read_iops:float; random_read_p95_ms:float; random_read_kib:int; random_reads:int; direct_cache_hint:bool; note:str
    def to_dict(self): return asdict(self)


def _nocache(fd:int)->bool:
    if platform.system()!="Darwin" or fcntl is None:return False
    try: fcntl.fcntl(fd,getattr(fcntl,"F_NOCACHE",48),1);return True
    except OSError:return False


def _random_offsets(total:int,read_size:int,count:int)->list[int]:
    if read_size>total: raise ValueError("random read size cannot exceed benchmark file size")
    rng=random.Random(0x4F5554455252414D); max_page=max(0,(total-read_size)//4096); return [rng.randint(0,max_page)*4096 for _ in range(count)]


def benchmark_disk(path:str|Path,*,size_mib:int=256,chunk_mib:int=4,random_read_kib:int=1024,random_reads:int=128)->DiskBenchmark:
    if not 32<=size_mib<=_MAX_BENCHMARK_SIZE_MIB: raise ValueError(f"size_mib must be between 32 and {_MAX_BENCHMARK_SIZE_MIB}")
    if chunk_mib<1 or chunk_mib>min(size_mib,_MAX_CHUNK_MIB): raise ValueError(f"chunk_mib must be between 1 and min(size_mib, {_MAX_CHUNK_MIB})")
    if not 4<=random_read_kib<=_MAX_RANDOM_READ_KIB: raise ValueError(f"random_read_kib must be between 4 and {_MAX_RANDOM_READ_KIB}")
    if not 8<=random_reads<=_MAX_RANDOM_READS: raise ValueError(f"random_reads must be between 8 and {_MAX_RANDOM_READS}")
    root=Path(path).expanduser().resolve(); root.mkdir(parents=True,exist_ok=True); total=size_mib*_MIB; chunk_size=chunk_mib*_MIB; random_size=random_read_kib*_KIB
    if random_size>total: raise ValueError("random_read_kib cannot exceed size_mib")
    free_bytes=shutil.disk_usage(root).free; required_free=total+max(64*_MIB,total//10)
    if free_bytes<required_free: raise RuntimeError(f"disk benchmark needs about {required_free/_MIB:.0f} MiB free including safety slack; only {free_bytes/_MIB:.0f} MiB is available")
    chunk=secrets.token_bytes(chunk_size); fd,tmp_name=tempfile.mkstemp(prefix="outerram-diskbench-",suffix=".bin",dir=root); os.close(fd); direct=False
    try:
        fd=os.open(tmp_name,os.O_WRONLY|os.O_TRUNC)
        try:
            direct=_nocache(fd) or direct; remaining=total; start=time.perf_counter()
            while remaining:
                data=chunk if remaining>=chunk_size else chunk[:remaining]; written=os.write(fd,data)
                if written!=len(data): raise IOError(f"short write: {written}/{len(data)}")
                remaining-=written
            os.fsync(fd); write_seconds=time.perf_counter()-start
        finally: os.close(fd)
        fd=os.open(tmp_name,os.O_RDONLY)
        try:
            direct=_nocache(fd) or direct; read_bytes=0; start=time.perf_counter()
            while True:
                data=os.read(fd,chunk_size)
                if not data: break
                read_bytes+=len(data)
            read_seconds=time.perf_counter()-start
        finally: os.close(fd)
        if read_bytes!=total: raise IOError(f"short benchmark read: {read_bytes}/{total}")
        offsets=_random_offsets(total,random_size,random_reads); latencies=[]; random_bytes=0; fd=os.open(tmp_name,os.O_RDONLY)
        try:
            direct=_nocache(fd) or direct; start=time.perf_counter()
            for offset in offsets:
                one=time.perf_counter(); data=os.pread(fd,random_size,offset); elapsed=time.perf_counter()-one
                if len(data)!=random_size: raise IOError(f"short random benchmark read: {len(data)}/{random_size} at {offset}")
                latencies.append(elapsed); random_bytes+=len(data)
            random_seconds=time.perf_counter()-start
        finally: os.close(fd)
        sorted_ms=sorted(v*1000 for v in latencies); p95_index=max(0,min(len(sorted_ms)-1,int((len(sorted_ms)*.95)+.999999)-1)); p95_ms=sorted_ms[p95_index] if sorted_ms else 0.0; random_mib=random_bytes/_MIB
        note="Sequential plus explicit random-range synthetic bandwidth. Random reads better approximate SSD expert-cache misses; real inference also depends on cache hit rate, range coalescing, page cache behavior, compute overlap and thermal state."
        if platform.system()!="Darwin": note+=" F_NOCACHE is unavailable on this host, so random results may include OS page-cache effects."
        return DiskBenchmark(str(root),size_mib,round(size_mib/max(write_seconds,1e-9),1),round(size_mib/max(read_seconds,1e-9),1),round(random_mib/max(random_seconds,1e-9),1),round(random_reads/max(random_seconds,1e-9),1),round(p95_ms,3),random_read_kib,random_reads,direct,note)
    finally:
        try: os.unlink(tmp_name)
        except FileNotFoundError: pass
