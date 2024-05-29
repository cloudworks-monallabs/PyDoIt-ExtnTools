from fabric import Connection
import hashlib
import os
from patchwork.files import exists

# Specify the additional SSH options as a dictionary
ssh_options = {
    'StrictHostKeyChecking': 'no',
    'UserKnownHostsFile': '/dev/null',
}


class RemoteFilesDep(object):
    """Custom uptodate class to check the modification state of remote files using MD5 hash"""

    def __init__(self, fabric_conn,  remote_files):
        """
        unable to pickle fabric connection object:
        using ipv6
        """

        self.fabric_conn = fabric_conn
        self.remote_files = remote_files
        self.modified_state = self.compute_remote_files_md5()

    def compute_remote_files_md5(self):
        # Initialize an empty MD5 hash
        combined_md5 = hashlib.md5()
        for remote_file in self.remote_files:
            if exists(self.fabric_conn, remote_file):
                file_md5 = self.compute_file_md5(remote_file)
                combined_md5.update(file_md5.encode())
        return combined_md5.hexdigest()

    def compute_file_md5(self, remote_file):
        # Run the md5sum command remotely to compute the MD5 hash
        result = self.fabric_conn.run(f'gmd5sum {remote_file}', hide=True)
        md5_hash = result.stdout.split()[0]
        return md5_hash

    def __call__(self, task, values):
        self.modified_state = self.compute_remote_files_md5()

        def save_now():
            """
            save the current state here
            """
            return {'modified_state': self.modified_state}
        task.value_savers.append(save_now)
        prev_modified_state = values.get('modified_state', None)

        if prev_modified_state is None:
            # this is the first check for modification
            return False

        # compare prev_modified and current computed value
        if prev_modified_state == self.modified_state:
            print("in RemoteFileDep: dependency is uptodate")

            return True
        print("in RemoteFileDep: dependency is not uptodate...rerun task")

        return False
