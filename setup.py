from setuptools import setup, find_packages
import sys, os

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()
NEWS = open(os.path.join(here, 'NEWS.txt')).read()

version = '0.7'

install_requires = [
    'PyYAML',
    'SQLAlchemy',
    'numpy',
    'Pydap >=3.2.1',
    'pydap.handlers.csv >=0.3'
]

setup(name='pydap.handlers.sql',
    version=version,
    description="An SQL handler for Pydap",
    long_description=README + '\n\n' + NEWS,
    classifiers=[
      # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    ],
    keywords="sql database opendap dods dap data science climate oceanography meteorology'",
    author='Roberto De Almeida',
    author_email='roberto@dealmeida.net',
    url='http://pydap.org/handlers.html#sql',
    license='MIT',
    packages=find_packages('src'),
    package_dir = {'': 'src'},
    namespace_packages = ['pydap', 'pydap.handlers'],
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
    dependency_links = ['https://github.com/pacificclimate/pydap-pdp/tarball/master#egg=Pydap-3.2.2',
                        'https://github.com/pacificclimate/pydap.handlers.csv/tarball/master#egg=pydap.handlers.csv-0.3'],
    entry_points="""
        [pydap.handler]
        sql = pydap.handlers.sql:SQLHandler
    """,
)
