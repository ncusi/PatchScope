import hashlib
from urllib.parse import urlencode

import panel as pn


@pn.cache
def gravatar_url(email: str, size: int = 16) -> str:
    # https://docs.gravatar.com/api/avatars/python/

    # Set default parameters
    # ...

    # Encode the email to lowercase and then to bytes
    email_encoded = email.lower().encode('utf-8')

    # Generate the SHA256 hash of the email
    email_hash = hashlib.sha256(email_encoded).hexdigest()

    # https://docs.gravatar.com/api/avatars/images/
    # Construct the URL with encoded query parameters
    query_params = urlencode({'s': str(size)})  # NOTE: will be needed for 'd' parameter
    url = f"https://www.gravatar.com/avatar/{email_hash}?{query_params}"

    return url
