from setuptools import setup, find_packages
from noopy import VERSION

print find_packages()

setup(
        name='noopy',
        packages=find_packages(),
        include_package_data=True,
        version=VERSION,
        description=('A no-ops(serverless) oriented web framework'
                     'using AWS lambda & API Gateway'),
        license='MIT License',
        author='Seungyeon Joshua Kim(Acuros)',
        author_email='acuroskr' '@' 'gmail.com',
        install_requires=[
          'boto3'
        ],
        entry_points={
          'console_scripts': [
              'noopy-admin=noopy.admin:main'
          ]
        },
        classifiers=[
          'Development Status :: 2 - Pre-Alpha',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 2.7',
          'Topic :: Internet :: WWW/HTTP'
        ]
)
