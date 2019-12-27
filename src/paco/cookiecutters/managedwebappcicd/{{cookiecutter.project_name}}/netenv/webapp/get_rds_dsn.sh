!Sub |
    #!/bin/bash

    DATABASE_INFO=`aws secretsmanager get-secret-value --secret-id "${DatabasePasswordarn}" --query SecretString --region ${AWS::Region} --output text`

    PASSWORD=`echo $DATABASE_INFO | jq '.password'`
    PASSWORD=`echo $PASSWORD | sed -e 's/^"//' -e 's/"$//'`

    HOST=`echo $DATABASE_INFO | jq '.host'`
    HOST=`echo $HOST | sed -e 's/^"//' -e 's/"$//'`

    USERNAME=`echo $DATABASE_INFO | jq '.username'`
    USERNAME=`echo $USERNAME | sed -e 's/^"//' -e 's/"$//'`

    # The \\ are only needed so that the sed expression works
    # in the later deploy/config_app.sh deploy script
    echo mysql+mysqlconnector:\\/\\/$USERNAME:$PASSWORD@$HOST\\/saas
