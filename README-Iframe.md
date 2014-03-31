Authenticating using the Toopher `<iframe>`
===========================================
Toopher's `<iframe>`-based authentication flow is the simplest way for web developers to integrate Toopher Two-Factor Authentication into an application.

## Toopher `<iframe>` Authentication Overview

The `iframe`-based authentication flow works by inserting an `<iframe>` element into the HTML displayed to the user after a successful username/password validation (but before they are actually logged-in to the service).  The iframe URL is generated by our library and its content is served from the Toopher API server.  The iframe guides the user through the process of authenticating with Toopher.  Once complete, the iframe will return the result of the authentication to your server by `POST`ing the response via HTML to an endpoint of your choice.  Your server validates the cryptographic signature using our library which determines whether or not the user successfully authenticated.

Two distinct iframe flows are required: 

* the *Pairing* request is used to pair a user account with a particular mobile device (this is typically a one-time process)
* the *Authentication* request to authenticate a particular action on behalf of a user

## Authentication Workflow
### Primary Authentication
We recommend using some form of primary authentication before initiating a Toopher authentication request.  Typical primary authentication methods involve verifying that the user has a valid username and password to access the resource being protected.

### Step 1: Embed a request in an `<iframe>`
After verifying the user's primary authentication, but before Assuming the user's primary authentication checks out, the next step is to kickoff Toopher authentication.

1. Generate a URI by specifying the request parameters to the library as detailed below
1. Display a webpage to your user that embeds this URI within an iframe element.  The markup requirements for the iframe element are described in the "HTML Markup" section

### Step 2: Validate the result
1. Toopher-iframe results posted back to server
1. Server calls `ToopherIframe.validate()` to verify that result is valid.  `.validate()` returns a `Map` of trusted data if the signature is valid, or throws a `SignatureValidationError` if the signature is invalid.
1. The server should check for possible errors returned by the API in the `error_code` map entry
1. If no errors were returned, the result of the authentication is in the `granted` map entry

### HTML markup
The `<iframe>` element must have an id of `toopher_iframe`.

Pages that include the Toopher Authentication or Pairing iframe must include the accompanying javascript library `toopher-web.js` (located in `/assets/js/` in this repository).  Toopher's Authentication and Pairing `<iframe>` content is designed for a minimum size of 400x300 px.  In the example below, `{{IFRAME_REQUEST_URL}}` is the Authentication or Pairing URL generated by the ToopherIframe library.  `{{POSTBACK_URL}}` is the path on your server where the Toopher-Iframe will submit the result of the authentication when it is finished.

    <!-- toopher-web.js requires jQuery.  uncomment the following line to source it from CDNJS if it is not already included in your page -->
    <!-- <script src="//cdnjs.cloudflare.com/ajax/libs/jquery/1.11.0/jquery.min.js"></script> -->
    <script src="/js/toopher-web.js"></script>
    <iframe id="toopher_iframe" src="{{IFRAME_REQUEST_URL}}" toopher_postback="{{POSTBACK_URL}}" style="display:inline-block; height:300px; width:100%;"></iframe>

There is no difference in the markup required for a Pairing vs. an Authentication iframe request (the generated URI embeds all relevant information).

# Examples

#### Generating an Authentication iframe URI
Every Toopher Authentication session should include a unique `request_token` - a randomized string that is included in the signed request to the Toopher API and returned in the signed response from the Toopher `<iframe>`.  To guard against potential replay attacks, your code should validate that the returned `request_token` is the same one used to create the request.

Creating a random request token and storing it in the server-side session using Django:

    import random, string
    request_token = ''.join(random.choice(string.lowercase + string.digits) for i in range(15))
    request.session['ToopherRequestToken'] = request_token

The Toopher Authentication API provides the requester a rich set of controls over authentication parameters.

    auth_iframe_url = iframe_api.auth_uri(username, reset_email, action_name, automation_allowed, challenge_required, request_token, requester_metadata, ttl);

For the simple case of authenticating a user at login, a `login_uri` helper method is available:

    login_iframe_url = iframe_api.login_uri(username, reset_email, request_token)

#### Generating a Pairing iframe URI

    pair_iframe_url = iframe_api.pair_uri(username, reset_email)

#### Validating postback data from Authentication iframe and parsing API errors
In this example, `data` is a `dict` of the form data POSTed to your server from the Toopher Authentication iframe.  You should replace the commented blocks with code appropriate for the condition described in the comment.

    request_token = request.session.get('ToopherRequestToken')
    // invalidate the Request Token to guard against replay attacks
    if 'ToopherRequestToken' in request.session:
        del request.session['ToopherRequestToken']

    try:
        validated_data = iframe_api.validate(data, request_token)
        if 'error_code' in validated_data:
            error_code = validated_data['error_code']
            # check for API errors

            if error_code == ToopherIframe.ERROR_CODE_PAIRING_DEACTIVATED:
                # User deleted the pairing on their mobile device.
                # 
                # Your server should display a Toopher Pairing iframe so their account can be re-paired
                #
            elif error_code == ToopherIframe.ERROR_CODE_USER_OPT_OUT:
                # User has been marked as "Opt-Out" in the Toopher API
                #
                # If your service allows opt-out, the user should be granted access.
                #
            elif error_code == ToopherIframe.ERROR_CODE_USER_UNKNOWN:
                # User has never authenticated with Toopher on this server
                #
                # Your server should display a Toopher Pairing iframe so their account can be paired
                #
        else:
            # signature is valid, and no api errors.  check authentication result
            auth_pending = validated_data.get('pending').lower() == 'true'
            auth_granted = validated_data.get('granted').lower() == 'true'

            # authentication_result is the ultimate result of Toopher second-factor authentication
            authentication_result = auth_granted and not auth_pending
    except toopher.SignatureValidationError, e:
        # signature was invalid.  User should not authenticated
        # 
        # e.message will return more information about what specifically
        # went wrong (incorrect session token, expired TTL, invalid signature)
        # 