from setuptools import find_packages, setup

package_name = "stem_task_server"

setup(
    name=package_name,
    version="0.0.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="SailorMoonQ",
    maintainer_email="219774340+SailorMoonQ@users.noreply.github.com",
    description="Task orchestration and behavior trees for STEM-E.",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={"console_scripts": []},
)
