PROJECT_NAME = '$project_name'
ACCOUNT_ID = '$account_id'  # Your AWS account id
LAMBDA = {
        'Prefix': '$lambda_prefix',  # Prefix for lambda function name
        'Role': '$role_arn',  # Role arn to be granted to lambda function
}
LAMBDA_MODULES = [  # python files use noopy.endpoint.decorators.endpoint
        'views'
]
