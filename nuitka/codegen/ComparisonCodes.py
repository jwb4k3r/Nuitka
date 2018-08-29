#     Copyright 2018, Kay Hayen, mailto:kay.hayen@gmail.com
#
#     Part of "Nuitka", an optimizing Python compiler that is compatible and
#     integrates with CPython, but also works on its own.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
""" Comparison related codes.

Rich comparisons, "in", and "not in", also "is", and "is not", and the
"isinstance" check as used in conditions, as well as exception matching.
"""

from . import OperatorCodes
from .CodeHelpers import generateExpressionCode
from .ErrorCodes import getErrorExitBoolCode, getErrorExitCode, getReleaseCodes


def generateComparisonExpressionCode(to_name, expression, emit, context):
    left_name = context.allocateTempName("compexpr_left")
    right_name = context.allocateTempName("compexpr_right")

    generateExpressionCode(
        to_name    = left_name,
        expression = expression.getLeft(),
        emit       = emit,
        context    = context
    )
    generateExpressionCode(
        to_name    = right_name,
        expression = expression.getRight(),
        emit       = emit,
        context    = context
    )

    comparator  = expression.getComparator()

    if comparator in OperatorCodes.containing_comparison_codes:
        needs_check = expression.getRight().mayRaiseExceptionIn(
            BaseException,
            expression.getLeft()
        )

        res_name = context.getIntResName()

        emit(
             "%s = PySequence_Contains( %s, %s );" % (
                res_name,
                right_name, # sequence goes first in the API.
                left_name
            )
        )

        getErrorExitBoolCode(
            condition     = "%s == -1" % res_name,
            release_names = (left_name, right_name),
            needs_check   = needs_check,
            emit          = emit,
            context       = context
        )

        emit(
            to_name.getCType().getAssignmentCodeFromBoolCondition(
                to_name   = to_name,
                condition = "%s == %d" % (
                    res_name,
                    1 if comparator == "In" else 0
                )
            )
        )

        return
    elif comparator == "Is":
        emit(
            to_name.getCType().getAssignmentCodeFromBoolCondition(
                to_name   = to_name,
                condition = "%s == %s" % (left_name, right_name)
            )
        )

        getReleaseCodes(
            release_names = (left_name, right_name),
            emit          = emit,
            context       = context
        )

        return
    elif comparator == "IsNot":
        emit(
            to_name.getCType().getAssignmentCodeFromBoolCondition(
                to_name   = to_name,
                condition = "%s != %s" % (left_name, right_name)
            )
        )

        getReleaseCodes(
            release_names = (left_name, right_name),
            emit          = emit,
            context       = context
        )

        return
    elif comparator in OperatorCodes.rich_comparison_codes:
        needs_check = expression.mayRaiseExceptionBool(BaseException)

        c_type = to_name.getCType()

        if c_type.c_type == "PyObject *":
            helper = "RICH_COMPARE_%s" % (
                OperatorCodes.rich_comparison_codes[ comparator ]
            )

            if not context.mayRecurse() and comparator == "Eq":
                helper += "_NORECURSE"

            emit(
                "%s = %s( %s, %s );" % (
                    to_name,
                    helper,
                    left_name,
                    right_name
                )
            )

            getErrorExitCode(
                check_name    = to_name,
                release_names = (left_name, right_name),
                needs_check   = needs_check,
                emit          = emit,
                context       = context
            )

            context.addCleanupTempName(to_name)
        elif c_type.c_type == "nuitka_bool":
            res_name = context.getIntResName()

            helper = OperatorCodes.rich_comparison_codes[comparator]
            if not context.mayRecurse() and comparator == "Eq":
                helper += "_NORECURSE"

            emit(
                 "%s = RICH_COMPARE_BOOL_%s( %s, %s );" % (
                    res_name,
                    helper,
                    left_name,
                    right_name
                )
            )

            getErrorExitBoolCode(
                condition     = "%s == -1" % res_name,
                release_names = (left_name, right_name),
                needs_check   = needs_check,
                emit          = emit,
                context       = context
            )

            emit(
                c_type.getAssignmentCodeFromBoolCondition(
                    to_name   = to_name,
                    condition = "%s != 0" % res_name
                )
            )
        else:
            assert False, to_name.c_type

        return
    elif comparator == "exception_match":
        needs_check = expression.mayRaiseExceptionBool(BaseException)

        res_name = context.getIntResName()

        emit(
             "%s = EXCEPTION_MATCH_BOOL( %s, %s );" % (
                res_name,
                left_name,
                right_name
            )
        )

        getErrorExitBoolCode(
            condition     = "%s == -1" % res_name,
            release_names = (left_name, right_name),
            needs_check   = needs_check,
            emit          = emit,
            context       = context
        )

        emit(
            to_name.getCType().getAssignmentCodeFromBoolCondition(
                to_name   = to_name,
                condition = "%s != 0" % res_name
            )
        )
    else:
        assert False, comparator


def generateBuiltinIsinstanceCode(to_name, expression, emit, context):
    inst_name = context.allocateTempName("isinstance_inst")
    cls_name = context.allocateTempName("isinstance_cls")

    generateExpressionCode(
        to_name    = inst_name,
        expression = expression.getInstance(),
        emit       = emit,
        context    = context
    )
    generateExpressionCode(
        to_name    = cls_name,
        expression = expression.getCls(),
        emit       = emit,
        context    = context
    )


    res_name = context.getIntResName()

    emit(
        "%s = Nuitka_IsInstance( %s, %s );" % (
            res_name,
            inst_name,
            cls_name
        )
    )

    getErrorExitBoolCode(
        condition     = "%s == -1" % res_name,
        release_names = (inst_name, cls_name),
        emit          = emit,
        context       = context
    )

    emit(
        to_name.getCType().getAssignmentCodeFromBoolCondition(
            to_name   = to_name,
            condition = "%s != 0" % res_name
        )
    )
