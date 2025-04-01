from sftp_server.sqlite_auth import AuthenticationError


class PermissionsManager(object):
    """
    Manages permissions on a directory tree.

    An `authenticate` method must be supplied which should take a username and
    password and return a list of groups to which they belong (or None if the
    credentials are invalid)

    The permissions are specified via a dict which maps paths to sets of groups
    which have write access on that path. (Write access on a path implies write
    access on all its children.)

    All valid users have read access to all files.

    If `required_group` is set then users must belong to this group to be
    considered valid.

    The class provides a `get_user` method which can be passed to an `SFTPServer`
    instance to handle authentication and permissions.
    """

    def __init__(self, authenticate=None):
        if authenticate:
            self.authenticate = authenticate

    def authenticate(self, username, password):
        # Should return the list of groups the user belongs to if user
        # authenticates correctly, and None otherwise
        raise NotImplementedError()

    def get_user(self, username, password):
        try:
            pages = self.authenticate(username, password)
            return User(self, pages, username)
        except AuthenticationError:
            return None

    def has_read_access(self, path, pages, block_root=False):
        # All users have read access everywhere
        return True

    def has_write_access(self, path, pages, block_root=False):
        if not self.authenticate:
            return False
        for owned_site in pages:
            if path.startswith(owned_site):
                if block_root and path == owned_site:
                    return False
                return True
        return False


class User(object):

    def __init__(self, manager, pages, user_id):
        self.manager = manager
        self.pages = pages
        self.user_id = user_id

    def has_read_access(self, path, _):
        return self.manager.has_read_access(path, self.pages, False)

    def has_write_access(self, path, block_root=False):
        return self.manager.has_write_access(path, self.pages, block_root)

    def __str__(self):
        return '<%s>' % self.user_id
