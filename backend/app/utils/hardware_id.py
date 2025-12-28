"""
Hardware-based machine ID generator
Prevents spoofing by using CPU and MAC address
"""
import hashlib
import uuid
import platform
import subprocess
import re


def get_hardware_id():
    """
    Generate a unique hardware-based machine ID
    Combines CPU ID and MAC address for uniqueness
    Returns a 32-character hex string
    """
    try:
        # Get CPU identifier
        cpu_id = _get_cpu_id()
        
        # Get MAC address
        mac = _get_mac_address()
        
        # Combine and hash
        hw_string = f"{cpu_id}-{mac}-{platform.system()}"
        hw_hash = hashlib.sha256(hw_string.encode()).hexdigest()[:32]
        
        return hw_hash
    except Exception as e:
        print(f"Warning: Could not generate hardware ID: {e}")
        # Fallback to hostname + MAC
        fallback = f"{platform.node()}-{uuid.getnode()}"
        return hashlib.sha256(fallback.encode()).hexdigest()[:32]


def _get_cpu_id():
    """Get CPU identifier based on OS"""
    try:
        system = platform.system()
        
        if system == "Windows":
            # Get Windows CPU ProcessorId
            output = subprocess.check_output(
                "wmic cpu get ProcessorId", 
                shell=True
            ).decode()
            cpu_id = re.findall(r'[A-Z0-9]+', output)[1] if len(re.findall(r'[A-Z0-9]+', output)) > 1 else "UNKNOWN"
            return cpu_id
            
        elif system == "Linux":
            # Get Linux CPU serial
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if 'Serial' in line:
                        return line.split(':')[1].strip()
            # Fallback to processor model
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if 'model name' in line:
                        return hashlib.md5(line.encode()).hexdigest()[:16]
                        
        elif system == "Darwin":  # macOS
            output = subprocess.check_output(
                ["ioreg", "-l"], 
                stderr=subprocess.DEVNULL
            ).decode()
            match = re.search(r'IOPlatformSerialNumber.*"(.+)"', output)
            if match:
                return match.group(1)
        
        # Fallback
        return platform.processor() or "UNKNOWN"
        
    except Exception as e:
        print(f"CPU ID error: {e}")
        return "UNKNOWN"


def _get_mac_address():
    """Get MAC address as formatted string"""
    try:
        mac = uuid.getnode()
        mac_str = ':'.join(['{:02x}'.format((mac >> elements) & 0xff) 
                           for elements in range(0, 2*6, 2)][::-1])
        return mac_str
    except Exception as e:
        print(f"MAC address error: {e}")
        return "00:00:00:00:00:00"


def sanitize_machine_id(machine_id):
    """
    Sanitize machine ID to prevent injection attacks
    Only allows alphanumeric, dash, underscore
    """
    # Remove non-alphanumeric except dash and underscore
    safe_id = re.sub(r'[^a-zA-Z0-9\-_]', '', machine_id)
    
    # Prevent injection keywords
    forbidden = ['DESKTOP_ACTIVATED', 'used', 'verified', 'void', 'DROP', 'SELECT', 'INSERT', 'UPDATE', 'DELETE']
    for word in forbidden:
        safe_id = safe_id.replace(word, '').replace(word.lower(), '')
    
    # Limit length
    return safe_id[:64]


# Example usage and testing
if __name__ == "__main__":
    print("Hardware ID:", get_hardware_id())
    print("Sanitized test:", sanitize_machine_id("test-DROP-machine"))
