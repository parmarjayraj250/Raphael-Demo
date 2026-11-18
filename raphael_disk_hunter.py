import os, sys, time, threading, hashlib, shutil, re
from datetime import datetime

class RaphaelDiskHunter:
    """
    Autonomous Disk Bloat & Duplicate Hunter (With Mandatory Human Approval):
    - Identifies exact duplicate files (via size matching + chunked SHA-256 hashing)
    - Locates abandoned cache directories (__pycache__, .pytest_cache, .cache)
    - Scans Windows TEMP folders for stale files
    - Strict Safety: Keeps original files, never touches system files or .git/
    - Human Approval Gate: Only deletes after explicit user confirmation
    """
    def __init__(self, safety_manager, speak_func=None, alert_callback=None):
        self.safety_manager = safety_manager
        self.speak_func = speak_func
        self.alert_callback = alert_callback
        self._pending_clean_plan = None
        self._last_scan_time = 0
        self.running = False
        self._thread = None

        # Protected directories that must NEVER be touched
        self.protected_dir_substrings = [
            r"c:\windows", r"c:\program files", r"c:\program files (x86)",
            ".git", ".venv", "venv", "node_modules/npm"
        ]

    def _is_safe_path(self, path: str) -> bool:
        """Verifies path is safe to inspect/clean and not part of core OS/Git."""
        norm = os.path.abspath(path).lower()
        for prot in self.protected_dir_substrings:
            if prot in norm:
                return False
        return True

    def _hash_file(self, file_path: str, chunk_size: int = 65536) -> str | None:
        """Computes SHA-256 hash in chunks for memory-efficient duplicate detection."""
        hasher = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(chunk_size):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except (PermissionError, FileNotFoundError, OSError):
            return None

    def find_duplicates(self, target_dirs: list[str]) -> list[dict]:
        """
        Detects exact duplicate files across target directories.
        Returns a list of dicts: {'original': path, 'duplicate': path, 'size': bytes}.
        """
        size_map = {}
        # 1. Quick size indexing
        for root_dir in target_dirs:
            if not os.path.exists(root_dir) or not self._is_safe_path(root_dir):
                continue
            for root, _, files in os.walk(root_dir):
                if not self._is_safe_path(root):
                    continue
                for fname in files:
                    fpath = os.path.join(root, fname)
                    try:
                        # Skip symbolic links and files under 1 KB
                        if os.path.islink(fpath):
                            continue
                        sz = os.path.getsize(fpath)
                        if sz > 1024:
                            size_map.setdefault(sz, []).append(fpath)
                    except (PermissionError, FileNotFoundError, OSError):
                        continue

        # 2. Hash only files that share the exact same byte length
        duplicates = []
        for sz, path_list in size_map.items():
            if len(path_list) < 2:
                continue

            hash_map = {}
            for fpath in path_list:
                fhash = self._hash_file(fpath)
                if not fhash:
                    continue
                hash_map.setdefault(fhash, []).append(fpath)

            for fhash, identical_paths in hash_map.items():
                if len(identical_paths) > 1:
                    # Smart ranking: Original is the one WITHOUT 'copy' or '(N)' in name, earliest mtime
                    def _rank_original(p: str):
                        name = os.path.basename(p).lower()
                        is_copy = 1 if ("copy" in name or "duplicate" in name or re.search(r"(\(\d+\)|_\d+$)", name)) else 0
                        try:
                            mtime = os.path.getmtime(p)
                        except OSError:
                            mtime = time.time()
                        return (is_copy, mtime, len(p))

                    identical_paths.sort(key=_rank_original)
                    original = identical_paths[0]
                    for dup in identical_paths[1:]:
                        duplicates.append({
                            "original": original,
                            "duplicate": dup,
                            "size": sz
                        })

        return duplicates

    def find_cache_bloat(self, target_dirs: list[str]) -> list[dict]:
        """Locates abandoned development cache folders (__pycache__, .pytest_cache)."""
        cache_dirs = []
        cache_names = {"__pycache__", ".pytest_cache", ".parcel-cache", ".turbo"}
        for root_dir in target_dirs:
            if not os.path.exists(root_dir) or not self._is_safe_path(root_dir):
                continue
            for root, dirs, _ in os.walk(root_dir):
                if not self._is_safe_path(root):
                    continue
                for d in list(dirs):
                    if d in cache_names:
                        full_dir = os.path.join(root, d)
                        total_sz = 0
                        for r, _, files in os.walk(full_dir):
                            for f in files:
                                try:
                                    total_sz += os.path.getsize(os.path.join(r, f))
                                except OSError:
                                    pass
                        if total_sz > 0:
                            cache_dirs.append({
                                "path": full_dir,
                                "name": d,
                                "size": total_sz
                            })
        return cache_dirs

    def find_temp_bloat(self) -> list[dict]:
        """Scans top-level Windows TEMP for unneeded stale temporary files."""
        temp_files = []
        temp_dir = os.environ.get("TEMP")
        if not temp_dir or not os.path.exists(temp_dir):
            return temp_files

        try:
            now = time.time()
            # Fast, non-recursive top-level scan
            with os.scandir(temp_dir) as entries:
                for entry in entries:
                    if entry.is_file(follow_symlinks=False):
                        fname = entry.name.lower()
                        # Target clear temp markers
                        if fname.endswith((".tmp", ".log", ".dmp", ".bak", ".old")) or fname.startswith("~"):
                            try:
                                stat = entry.stat()
                                # Older than 6 hours
                                if now - stat.st_mtime > 21600 and stat.st_size > 1024:
                                    temp_files.append({"path": entry.path, "size": stat.st_size})
                                    if len(temp_files) >= 150:
                                        break
                            except OSError:
                                continue
        except Exception:
            pass
        return temp_files

    def scan_disk_bloat(self, custom_dirs: list[str] = None, scan_temp: bool = None) -> dict:
        """
        Executes a bloat scan across user directories and caches.
        Stages findings into _pending_clean_plan for user approval.
        """
        is_custom = bool(custom_dirs)
        dirs_to_scan = custom_dirs or []
        if not dirs_to_scan:
            dl = os.path.expanduser("~/Downloads")
            desktop = os.path.expanduser("~/Desktop")
            workspace = os.path.dirname(os.path.abspath(__file__))
            for p in [dl, desktop, workspace]:
                if os.path.exists(p) and p not in dirs_to_scan:
                    dirs_to_scan.append(p)

        should_scan_temp = scan_temp if scan_temp is not None else (not is_custom)
        duplicates = self.find_duplicates(dirs_to_scan)
        caches = self.find_cache_bloat(dirs_to_scan)
        temps = self.find_temp_bloat() if should_scan_temp else []

        total_bytes = (
            sum(d['size'] for d in duplicates) +
            sum(c['size'] for c in caches) +
            sum(t['size'] for t in temps)
        )

        plan = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "duplicates": duplicates,
            "caches": caches,
            "temps": temps,
            "total_reclaimable_bytes": total_bytes
        }
        self._pending_clean_plan = plan
        self._last_scan_time = time.time()
        return plan

    def get_scan_report(self) -> str:
        """Generates a structured, readable report of identified bloat."""
        if not self._pending_clean_plan:
            self.scan_disk_bloat()

        plan = self._pending_clean_plan
        mb_total = round(plan["total_reclaimable_bytes"] / (1024 * 1024), 1)
        gb_total = round(plan["total_reclaimable_bytes"] / (1024 * 1024 * 1024), 2)

        lines = [
            "🧹 RAPHAEL DISK BLOAT & DUPLICATE HUNTER REPORT",
            "─" * 48,
            f"• Scan Completed:      {plan['timestamp']}",
            f"• Total Reclaimable:   {mb_total} MB ({gb_total} GB)",
            f"• Duplicate Files:     {len(plan['duplicates'])} items ({round(sum(d['size'] for d in plan['duplicates'])/(1024*1024), 1)} MB)",
            f"• Stale Cache Folders: {len(plan['caches'])} folders ({round(sum(c['size'] for c in plan['caches'])/(1024*1024), 1)} MB)",
            f"• Stale Temp Files:    {len(plan['temps'])} files ({round(sum(t['size'] for t in plan['temps'])/(1024*1024), 1)} MB)"
        ]

        if plan["duplicates"]:
            lines.append("\n📁 Duplicate Files Identified (Safe to delete duplicates):")
            for d in plan["duplicates"][:5]:
                dup_name = os.path.basename(d['duplicate'])
                sz_kb = round(d['size'] / 1024, 1)
                lines.append(f"  • {dup_name} ({sz_kb} KB)\n    └─ Original: {os.path.basename(d['original'])}")
            if len(plan["duplicates"]) > 5:
                lines.append(f"  ... and {len(plan['duplicates']) - 5} more duplicate files.")

        if plan["caches"]:
            lines.append("\n📦 Cache & Build Folders Identified:")
            for c in plan["caches"][:4]:
                c_sz_mb = round(c['size'] / (1024 * 1024), 1)
                lines.append(f"  • {c['path']} ({c_sz_mb} MB)")

        if plan["total_reclaimable_bytes"] > 0:
            lines.append("\n⚠️ MANDATORY APPROVAL GATE:")
            lines.append("Say 'approve clean' or 'clean disk' to safely delete duplicate copies and caches.")
            lines.append("Say 'cancel clean' to discard this report without making changes.")
        else:
            lines.append("\n✓ Your drive is in pristine condition! No duplicate files or stale bloat detected.")

        return "\n".join(lines)

    def execute_clean(self) -> tuple[bool, str]:
        """
        MANDATORY HUMAN APPROVAL GATE:
        Safely deletes duplicate copies and cache directories only after user approval.
        Never deletes original files or protected paths.
        """
        if not self._pending_clean_plan:
            return False, "No pending disk clean plan found. Say 'scan disk' first."

        plan = self._pending_clean_plan
        freed_bytes = 0
        deleted_count = 0

        # 1. Delete duplicate files (NEVER touch originals!)
        for dup_item in plan.get("duplicates", []):
            dup_path = dup_item["duplicate"]
            orig_path = dup_item["original"]
            if dup_path != orig_path and os.path.exists(dup_path) and self._is_safe_path(dup_path):
                try:
                    os.remove(dup_path)
                    freed_bytes += dup_item["size"]
                    deleted_count += 1
                except Exception:
                    pass

        # 2. Delete cache directories
        for cache_item in plan.get("caches", []):
            c_path = cache_item["path"]
            if os.path.exists(c_path) and self._is_safe_path(c_path):
                try:
                    shutil.rmtree(c_path, ignore_errors=True)
                    freed_bytes += cache_item["size"]
                    deleted_count += 1
                except Exception:
                    pass

        # 3. Delete stale temp files
        for temp_item in plan.get("temps", []):
            t_path = temp_item["path"]
            if os.path.exists(t_path) and self._is_safe_path(t_path):
                try:
                    os.remove(t_path)
                    freed_bytes += temp_item["size"]
                    deleted_count += 1
                except Exception:
                    pass

        mb_freed = round(freed_bytes / (1024 * 1024), 1)
        self.safety_manager.log_audit(
            "DISK_HUNTER", "CLEAN_APPROVED", "INFO", True,
            f"Reclaimed {mb_freed} MB across {deleted_count} items"
        )
        self._pending_clean_plan = None
        return True, f"✓ Disk cleanup complete! Successfully reclaimed {mb_freed} MB of storage across {deleted_count} items."

    def cancel_clean(self) -> str:
        """Discards pending clean plan."""
        self._pending_clean_plan = None
        return "Disk cleanup plan discarded. No files were modified or deleted."
