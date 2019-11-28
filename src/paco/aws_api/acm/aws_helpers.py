def response_succeeded(response):
    """ Given a Boto response,
        return True if the response was successful
    """
    return response.get('ResponseMetadata', {}).get('HTTPStatusCode') == 200
